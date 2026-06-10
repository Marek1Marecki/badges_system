"""Architecture Contract Audit — zero external dependencies.

Sprawdza naruszenia kontraktów architektonicznych których nie wykrywa
ruff, mypy ani import-linter:

- Domain Purity: zakazane biblioteki w domain/ — whitelist (stdlib + lokalne moduły),
  z jawnym blokowaniem os, random, logging mimo że są w stdlib
- Determinism: datetime.now/utcnow, uuid4, random w domain/ i application/
- Logging: import logging/loguru w domain/
- DataFrame: użycie DataFrame w domain/
- Configuration: os.getenv poza bootstrap
- Python Version Consistency: .python-version, Dockerfile, pyproject.toml muszą być zgodne

Uruchamiany jako część `make check` — blokuje pipeline przy naruszeniu.

Konfiguracja w pyproject.toml:
    [tool.audit]
    domain_paths = ["domain", "apps/tasks/domain"]
    application_paths = ["application", "apps/tasks/application"]
    bootstrap_paths = ["bootstrap", "manage.py"]

Jeśli brak konfiguracji — używa domyślnych ścieżek (autodiscovery).
"""

import ast
import pathlib
import re
import sys
import tomllib
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------


@dataclass
class AuditConfig:
    domain_paths: list[pathlib.Path] = field(default_factory=list)
    application_paths: list[pathlib.Path] = field(default_factory=list)
    bootstrap_paths: list[pathlib.Path] = field(default_factory=list)

    @classmethod
    def from_pyproject(cls) -> AuditConfig:
        pyproject = ROOT / "pyproject.toml"
        config = cls()

        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            tool_audit = data.get("tool", {}).get("audit", {})

            domain_raw = tool_audit.get("domain_paths", [])
            app_raw = tool_audit.get("application_paths", [])
            bootstrap_raw = tool_audit.get("bootstrap_paths", [])

            config.domain_paths = [ROOT / p for p in domain_raw if (ROOT / p).exists()]
            config.application_paths = [ROOT / p for p in app_raw if (ROOT / p).exists()]
            config.bootstrap_paths = [ROOT / p for p in bootstrap_raw if (ROOT / p).exists()]

        # Autodiscovery jeśli pyproject nie ma sekcji [tool.audit]
        if not config.domain_paths:
            config.domain_paths = _autodiscover(ROOT, "domain")
        if not config.application_paths:
            config.application_paths = _autodiscover(ROOT, "application")
        if not config.bootstrap_paths:
            config.bootstrap_paths = _autodiscover_bootstrap(ROOT)

        return config


def _autodiscover(root: pathlib.Path, name: str) -> list[pathlib.Path]:
    """Znajdź wszystkie katalogi o danej nazwie, ignoruj .venv i node_modules."""
    results = []
    for p in root.rglob(name):
        if p.is_dir() and not any(part in {".venv", "venv", "node_modules", ".git", "__pycache__"} for part in p.parts):
            results.append(p)
    return results


def _autodiscover_bootstrap(root: pathlib.Path) -> list[pathlib.Path]:
    """Szukaj plików bootstrapowych."""
    candidates = ["bootstrap.py", "manage.py", "wsgi.py", "asgi.py", "main.py"]
    return [root / c for c in candidates if (root / c).exists()]


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def collect_python_files(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(path.rglob("*.py"))
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def parse_file(path: pathlib.Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _is_type_checking_node(node: ast.If) -> bool:
    """Zwraca True jeśli węzeł If to blok `if TYPE_CHECKING:`."""
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _collect_imports_from_stmts(
    stmts: list[ast.stmt],
    in_type_checking: bool,
    results: list[tuple[str, bool]],
) -> None:
    """Zbiera importy z listy statement'ów (nie rekurencyjnie przez ast.walk).

    Rekurencja tylko dla zagnieżdżonych bloków if TYPE_CHECKING — bez
    podwójnego liczenia które powodowało ast.walk na całym drzewie.
    """
    for node in stmts:
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name.split(".")[0], in_type_checking))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                results.append((node.module.split(".")[0], in_type_checking))
        elif isinstance(node, ast.If):
            if _is_type_checking_node(node):
                # Wnętrze bloku TYPE_CHECKING — importy oznaczamy jako is_type_checking=True
                _collect_imports_from_stmts(node.body, True, results)
                _collect_imports_from_stmts(node.orelse, True, results)
            else:
                # Zwykły blok if — przechodzimy rekurencyjnie
                _collect_imports_from_stmts(node.body, in_type_checking, results)
                _collect_imports_from_stmts(node.orelse, in_type_checking, results)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Importy wewnątrz funkcji/klas — traktujemy jak normalne
            _collect_imports_from_stmts(node.body, in_type_checking, results)


def get_imports(tree: ast.Module) -> list[tuple[str, bool]]:
    """Zwraca (moduł, is_type_checking) dla każdego importu w module.

    Używa manualnego przejścia po drzewie zamiast ast.walk, żeby uniknąć
    podwójnego raportowania importów z bloku TYPE_CHECKING — ast.walk
    odwiedza węzły rekurencyjnie, więc import z TYPE_CHECKING byłby
    zgłoszony raz jako is_type_checking=True i raz jako False.
    """
    results: list[tuple[str, bool]] = []
    _collect_imports_from_stmts(tree.body, False, results)
    return results


def get_attribute_calls(tree: ast.Module) -> list[str]:
    """Zbiera wywołania w postaci 'module.function(' — np. datetime.now."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    calls.append(f"{func.value.id}.{func.attr}")
                elif isinstance(func.value, ast.Attribute):
                    # np. datetime.datetime.now
                    calls.append(f"{func.value.attr}.{func.attr}")
    return calls


def has_name_usage(tree: ast.Module, name: str) -> bool:
    """Sprawdza czy identyfikator pojawia się w kodzie (Name node)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == name:
            return True
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


@dataclass
class Failure:
    category: str
    message: str
    file: pathlib.Path
    lineno: int | None = None
    is_type_checking: bool = False

    def __str__(self) -> str:
        suffix = " [TYPE_CHECKING — ukryte obejście!]" if self.is_type_checking else ""
        rel = self.file.relative_to(ROOT)
        location = f"{rel}:{self.lineno}" if self.lineno is not None else str(rel)
        return f"[{self.category}] {self.message} — {location}{suffix}"


def _get_import_nodes_with_lines(
    tree: ast.Module,
) -> list[tuple[str, bool, int]]:
    """Zwraca (moduł, is_type_checking, lineno) dla każdego importu.

    Analogia do get_imports(), ale zwraca też numer linii z węzła AST.
    """
    results: list[tuple[str, bool, int]] = []

    def collect(stmts: list[ast.stmt], in_tc: bool) -> None:
        for node in stmts:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    results.append((alias.name.split(".")[0], in_tc, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    results.append((node.module.split(".")[0], in_tc, node.lineno))
            elif isinstance(node, ast.If):
                if _is_type_checking_node(node):
                    collect(node.body, True)
                    collect(node.orelse, True)
                else:
                    collect(node.body, in_tc)
                    collect(node.orelse, in_tc)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                collect(node.body, in_tc)

    collect(tree.body, False)
    return results


def check_forbidden_imports(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """Domain Purity — zakazane biblioteki w domain/.

    Używa whitelisty (biblioteka standardowa + lokalne moduły) zamiast blacklisty.
    Wykrywa wszelkie importy 3rd-party (np. boto3, celery, pydantic), również
    te ukryte w bloku TYPE_CHECKING (klasyczne obejście kontraktu).
    Zgłasza numer linii naruszenia.
    """
    # 1. Pobierz wszystkie moduły biblioteki standardowej
    stdlib_modules = set(sys.stdlib_module_names)

    # 2. Wyjątki ze stdlib, które celowo blokujemy w domain/ (zgodnie z kontraktami)
    explicitly_forbidden_stdlib = {
        "os",  # domain/ nie czyta środowiska — konfiguracja przez bootstrap
        "random",  # niedeterminizm — patrz 17-determinism-contract.md
        "logging",  # logowanie to infrastruktura
    }

    # 3. Pobierz główne katalogi projektu (żeby pozwolić na importy wewnątrz aplikacji,
    #    np. `from domain import...` lub `from apps import...`)
    local_modules = {
        p.name
        for p in ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in {"__pycache__", "node_modules"}
    }

    # Suma dozwolonych modułów bazowych minus te celowo zablokowane
    allowed_bases = (stdlib_modules | local_modules) - explicitly_forbidden_stdlib

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        # _get_import_nodes_with_lines zwraca już bazowy moduł (po split(".")[0])
        for base_module, in_type_checking, lineno in _get_import_nodes_with_lines(tree):
            if base_module not in allowed_bases:
                failures.append(
                    Failure(
                        category="DOMAIN PURITY",
                        message=f"Non-stdlib import '{base_module}' is forbidden in domain layer",
                        file=path,
                        lineno=lineno,
                        is_type_checking=in_type_checking,
                    )
                )


def check_determinism(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """Determinism Contract — zakazane wywołania niedeterministyczne.

    Sprawdza domain/ i application/ — oba muszą być deterministyczne.
    Wykrywa zarówno wywołania z prefiksem (uuid.uuid4()) jak i bez (uuid4())
    — to drugie pojawia się po `from uuid import uuid4`.
    """
    forbidden_attr_calls = {
        "datetime.now",
        "datetime.utcnow",
        "uuid.uuid4",
        "random.random",
        "random.randint",
        "random.choice",
        "time.time",
    }
    # Wywołania bez prefiksu — po `from X import func`
    forbidden_bare_calls = {"uuid4", "randint", "choice"}

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        # Wywołania z prefiksem (moduł.funkcja)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                call_str: str | None = None

                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        call_str = f"{func.value.id}.{func.attr}"
                    elif isinstance(func.value, ast.Attribute):
                        call_str = f"{func.value.attr}.{func.attr}"

                if call_str and call_str in forbidden_attr_calls:
                    failures.append(
                        Failure(
                            category="DETERMINISM",
                            message=f"Non-deterministic call '{call_str}()' — use injected port",
                            file=path,
                            lineno=node.lineno,
                        )
                    )

                # Wywołania bare — np. uuid4() po from uuid import uuid4
                if isinstance(func, ast.Name) and func.id in forbidden_bare_calls:
                    failures.append(
                        Failure(
                            category="DETERMINISM",
                            message=f"Non-deterministic call '{func.id}()' — use injected port",
                            file=path,
                            lineno=node.lineno,
                        )
                    )


def check_dataframe_in_domain(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """DataFrame Contract — DataFrame nie może wejść do domain/."""
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "DataFrame":
                failures.append(
                    Failure(
                        category="DATAFRAME CONTRACT",
                        message="DataFrame usage detected — domain must use DTOs, not DataFrames",
                        file=path,
                        lineno=node.lineno,
                    )
                )
                break  # jedno zgłoszenie per plik wystarczy
            if isinstance(node, ast.Attribute) and node.attr == "DataFrame":
                failures.append(
                    Failure(
                        category="DATAFRAME CONTRACT",
                        message="DataFrame usage detected — domain must use DTOs, not DataFrames",
                        file=path,
                        lineno=node.lineno,
                    )
                )
                break


def check_env_access_in_application(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """Configuration Contract — os.getenv poza warstwą bootstrap.

    application/ nie może czytać zmiennych środowiskowych bezpośrednio.
    Konfiguracja jest wstrzykiwana przez bootstrap.

    Uwaga: infrastructure/ jest warstwą zewnętrzną i może zawierać os.getenv
    (np. infrastructure/config.py). Skrypt nie skanuje infrastructure/.

    Wykrywane wzorce:
    - os.getenv("KEY")          → ast.Attribute
    - environ.get("KEY")        → ast.Attribute
    - getenv("KEY")             → ast.Name (po: from os import getenv)
    - os.environ["KEY"]         → ast.Subscript
    """
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                call_str: str | None = None
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        call_str = f"{func.value.id}.{func.attr}"
                if call_str in {"os.getenv", "environ.get"}:
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message="os.getenv/environ.get in application/ — read env only in bootstrap",
                            file=path,
                            lineno=node.lineno,
                        )
                    )

                # Wykryj: from os import getenv; getenv("KEY")
                if isinstance(func, ast.Name) and func.id == "getenv":
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message=(
                                "bare getenv() in application/ — likely 'from os import getenv'; "
                                "read env only in bootstrap"
                            ),
                            file=path,
                            lineno=node.lineno,
                        )
                    )

            # Sprawdź os.environ[] (subscript access)
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message="os.environ[] access in application/ — read env only in bootstrap",
                            file=path,
                            lineno=node.lineno,
                        )
                    )


def check_python_version_consistency(failures: list[Failure]) -> None:
    """Documentation Contract — wersja Pythona musi być identyczna w trzech miejscach.

    Sprawdza .python-version, Dockerfile (FROM python:X.Y...) i pyproject.toml
    (requires-python). Rozbieżność jest naruszeniem kontraktu.

    Jeśli któryś z plików nie istnieje — ostrzeżenie, nie błąd (projekt może
    nie używać wszystkich trzech).

    pyproject.toml parsowany przez tomllib (nie regex) — gwarantuje poprawny
    odczyt niezależnie od formatowania pliku.
    """
    versions: dict[str, str | None] = {
        ".python-version": None,
        "Dockerfile": None,
        "pyproject.toml": None,
    }

    # .python-version — cały plik to wersja (np. "3.12" lub "3.12.0")
    pv_file = ROOT / ".python-version"
    if pv_file.exists():
        raw = pv_file.read_text().strip()
        # Normalizuj do major.minor (np. "3.12.3" → "3.12")
        m = re.match(r"^(\d+\.\d+)", raw)
        if m:
            versions[".python-version"] = m.group(1)

    # Dockerfile — FROM python:3.12-slim-bookworm lub FROM python:3.12.3-...
    dockerfile = ROOT / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text()
        # Szukaj pierwszego FROM python:X.Y (Stage 1 builder)
        m = re.search(r"FROM python:(\d+\.\d+)", text)
        if m:
            versions["Dockerfile"] = m.group(1)

    # pyproject.toml — requires-python przez tomllib (pewny odczyt, nie regex)
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        requires = data.get("project", {}).get("requires-python", "")
        if requires:
            # Wyciągnij major.minor z >=3.12, ==3.12.*, ~=3.12 itp.
            m = re.search(r"(\d+\.\d+)", requires)
            if m:
                versions["pyproject.toml"] = m.group(1)

    # Filtruj pliki które nie istnieją (None)
    found = {k: v for k, v in versions.items() if v is not None}

    if len(found) < 2:
        # Zbyt mało plików do porównania — nie blokuj, ostrzeż
        missing = [k for k, v in versions.items() if v is None]
        print(f"  [PYTHON VERSION] WARNING: Cannot verify — missing: {', '.join(missing)}")
        return

    unique_versions = set(found.values())
    if len(unique_versions) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in found.items())
        failures.append(
            Failure(
                category="PYTHON VERSION CONSISTENCY",
                message=f"Version mismatch: {detail} — all three must match",
                file=ROOT / "pyproject.toml",
            )
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run(config: AuditConfig) -> int:
    """Uruchamia wszystkie sprawdzenia i zwraca kod wyjścia (0 = PASS, 1 = FAIL).

    Nie używa globalnego stanu — każde wywołanie run() jest niezależne.
    Umożliwia testowanie unitowe bez resetu globalnych zmiennych.
    """
    failures: list[Failure] = []

    print("=== CONTRACT AUDIT ===\n")

    domain_files = collect_python_files(config.domain_paths)
    app_files = collect_python_files(config.application_paths)

    if not domain_files and not app_files:
        print("WARNING: No domain/ or application/ files found.")
        print("Configure paths in pyproject.toml [tool.audit] or check project structure.\n")

    print("Checking Python version consistency...")
    check_python_version_consistency(failures)

    if domain_files:
        print(f"Scanning domain/ ({len(domain_files)} files)...")
        check_forbidden_imports(domain_files, failures)
        check_determinism(domain_files, failures)
        check_dataframe_in_domain(domain_files, failures)

    if app_files:
        print(f"Scanning application/ ({len(app_files)} files)...")
        check_determinism(app_files, failures)
        check_env_access_in_application(app_files, failures)

    print()

    if failures:
        print(f"Audit FAILED — {len(failures)} violation(s):\n")
        for failure in failures:
            print(f"  ✗ {failure}")
        print()
        return 1

    print("Audit PASSED ✓")
    return 0


if __name__ == "__main__":
    config = AuditConfig.from_pyproject()
    sys.exit(run(config))
