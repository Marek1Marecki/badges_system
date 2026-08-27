"""Architecture contract audit with zero external dependencies.

This script enforces architecture rules that are harder to express in ruff,
mypy or import-linter alone:
- domain purity
- determinism in domain/application
- no side effects in domain
- layer dependency rules
- ORM isolation
- port implementation boundaries
- dependency cycle detection
- dependency graph export as a first-class architecture artifact
"""

import ast
import html
import pathlib
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORT_GRAPH = True
GRAPH_DOT_OUTPUT = ROOT / "dependencies.dot"
GRAPH_SVG_OUTPUT = ROOT / "dependencies.svg"

LAYER_MAP = {
    "domain": "domain",
    "application": "application",
    "infrastructure": "infrastructure",
    "apps": "interface",
}

LAYER_COLORS = {
    "domain": "lightblue",
    "application": "lightgreen",
    "ports": "khaki",
    "infrastructure": "orange",
    "interface": "pink",
    "other": "white",
}

GRAPH_LAYER_ORDER = ["domain", "application", "ports", "infrastructure", "interface", "other"]
LOCAL_LAYER_ROOTS = set(LAYER_MAP) | {"ports"}

FORBIDDEN_DEPENDENCIES = {
    "domain": {"application", "ports", "infrastructure", "interface"},
    "application": {"infrastructure", "interface"},
    "ports": {"infrastructure", "interface"},
}

FORBIDDEN_SIDE_EFFECT_FUNCTIONS = {"open", "print", "sleep"}
FORBIDDEN_SIDE_EFFECT_MODULES = {"httpx", "logging", "requests", "subprocess", "time"}
ORM_MODULE_PREFIXES = {"django.db", "peewee", "sqlalchemy"}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class AuditConfig:
    """Konfiguracja audytu kontraktów."""

    domain_paths: list[pathlib.Path] = field(default_factory=list)
    application_paths: list[pathlib.Path] = field(default_factory=list)
    bootstrap_paths: list[pathlib.Path] = field(default_factory=list)

    @classmethod
    def from_pyproject(cls) -> "AuditConfig":
        """Wczytuje konfigurację z pyproject.toml."""
        pyproject = ROOT / "pyproject.toml"
        config = cls()

        if pyproject.exists():
            with open(pyproject, "rb") as file_obj:
                data = tomllib.load(file_obj)
            tool_audit = data.get("tool", {}).get("audit", {})

            domain_raw = tool_audit.get("domain_paths", [])
            app_raw = tool_audit.get("application_paths", [])
            bootstrap_raw = tool_audit.get("bootstrap_paths", [])

            config.domain_paths = [ROOT / value for value in domain_raw if (ROOT / value).exists()]
            config.application_paths = [ROOT / value for value in app_raw if (ROOT / value).exists()]
            config.bootstrap_paths = [ROOT / value for value in bootstrap_raw if (ROOT / value).exists()]

        if not config.domain_paths:
            config.domain_paths = _autodiscover(ROOT, "domain")
        if not config.application_paths:
            config.application_paths = _autodiscover(ROOT, "application")
        if not config.bootstrap_paths:
            config.bootstrap_paths = _autodiscover_bootstrap(ROOT)

        return config


def _autodiscover(root: pathlib.Path, name: str) -> list[pathlib.Path]:
    """

    Args:
      root: pathlib.Path:
      name: str:
      root: pathlib.Path:
      name: str:

    Returns:

    """
    results = []
    for path in root.rglob(name):
        if path.is_dir() and not any(
            part in {".venv", "venv", "node_modules", ".git", "__pycache__"} for part in path.parts
        ):
            results.append(path)
    return results


def _autodiscover_bootstrap(root: pathlib.Path) -> list[pathlib.Path]:
    """

    Args:
      root: pathlib.Path:
      root: pathlib.Path:

    Returns:

    """
    candidates = ["bootstrap.py", "manage.py", "wsgi.py", "asgi.py", "main.py"]
    return [root / candidate for candidate in candidates if (root / candidate).exists()]


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportReference:
    """Referencja importu w grafie zależności."""

    base_module: str
    full_module: str
    is_type_checking: bool
    lineno: int


def collect_python_files(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    """

    Args:
      paths: list[pathlib.Path]:
      paths: list[pathlib.Path]:

    Returns:

    """
    files: list[pathlib.Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(path.rglob("*.py"))
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return sorted(set(files))


def parse_file(path: pathlib.Path) -> ast.Module | None:
    """

    Args:
      path: pathlib.Path:
      path: pathlib.Path:

    Returns:

    """
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def module_name_for_path(path: pathlib.Path) -> str:
    """

    Args:
      path: pathlib.Path:
      path: pathlib.Path:

    Returns:

    """
    relative = path.relative_to(ROOT)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = path.stem
    return ".".join(parts)


def package_parts_for_path(path: pathlib.Path) -> list[str]:
    """

    Args:
      path: pathlib.Path:
      path: pathlib.Path:

    Returns:

    """
    relative = path.relative_to(ROOT)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        return parts[:-1]
    return parts[:-1]


def get_local_module_names() -> set[str]:
    """Zwraca zbiór nazw modułów lokalnych."""
    local_modules: set[str] = set()
    for path in ROOT.iterdir():
        if path.name.startswith(".") or path.name in {"__pycache__", "node_modules"}:
            continue
        if path.is_dir():
            local_modules.add(path.name)
        elif path.suffix == ".py":
            local_modules.add(path.stem)
    return local_modules


def is_local_module(module_name: str) -> bool:
    """

    Args:
      module_name: str:
      module_name: str:

    Returns:

    """
    if not module_name:
        return False
    return module_name.split(".")[0] in LOCAL_LAYER_ROOTS


def _resolve_relative_import(path: pathlib.Path, node: ast.ImportFrom, alias_name: str) -> str | None:
    """

    Args:
      path: pathlib.Path:
      node: ast.ImportFrom:
      alias_name: str:
      path: pathlib.Path:
      node: ast.ImportFrom:
      alias_name: str:

    Returns:

    """
    package_parts = package_parts_for_path(path)
    levels_up = max(node.level - 1, 0)

    if levels_up > len(package_parts):
        return None

    prefix = package_parts[: len(package_parts) - levels_up]
    if node.module:
        suffix = node.module.split(".")
    elif alias_name != "*":
        suffix = alias_name.split(".")
    else:
        suffix = []

    resolved_parts = [part for part in prefix + suffix if part]
    return ".".join(resolved_parts) or None


def _is_type_checking_node(node: ast.If) -> bool:
    """

    Args:
      node: ast.If:
      node: ast.If:

    Returns:

    """
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _collect_imports_from_stmts(
    path: pathlib.Path,
    statements: list[ast.stmt],
    in_type_checking: bool,
    results: list[ImportReference],
) -> None:
    """

    Args:
      path: pathlib.Path:
      statements: list[ast.stmt]:
      in_type_checking: bool:
      results: list[ImportReference]:
      path: pathlib.Path:
      statements: list[ast.stmt]:
      in_type_checking: bool:
      results: list[ImportReference]:

    Returns:

    """
    for node in statements:
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(
                    ImportReference(
                        base_module=alias.name.split(".")[0],
                        full_module=alias.name,
                        is_type_checking=in_type_checking,
                        lineno=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                for alias in node.names:
                    resolved = _resolve_relative_import(path, node, alias.name)
                    if resolved:
                        results.append(
                            ImportReference(
                                base_module=resolved.split(".")[0],
                                full_module=resolved,
                                is_type_checking=in_type_checking,
                                lineno=node.lineno,
                            )
                        )
                continue

            if node.module:
                results.append(
                    ImportReference(
                        base_module=node.module.split(".")[0],
                        full_module=node.module,
                        is_type_checking=in_type_checking,
                        lineno=node.lineno,
                    )
                )
        elif isinstance(node, ast.If):
            if _is_type_checking_node(node):
                _collect_imports_from_stmts(path, node.body, True, results)
                _collect_imports_from_stmts(path, node.orelse, True, results)
            else:
                _collect_imports_from_stmts(path, node.body, in_type_checking, results)
                _collect_imports_from_stmts(path, node.orelse, in_type_checking, results)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _collect_imports_from_stmts(path, node.body, in_type_checking, results)


def get_import_references(path: pathlib.Path, tree: ast.Module) -> list[ImportReference]:
    """

    Args:
      path: pathlib.Path:
      tree: ast.Module:
      path: pathlib.Path:
      tree: ast.Module:

    Returns:

    """
    results: list[ImportReference] = []
    _collect_imports_from_stmts(path, tree.body, False, results)
    return results


def detect_layer_from_parts(parts: tuple[str, ...] | list[str]) -> str | None:
    """

    Args:
      parts: tuple[str:
      ...] | list[str]:
      parts: tuple[str:

    Returns:

    """
    parts_set = set(parts)
    if "application" in parts_set and "ports" in parts_set:
        return "ports"
    for name, layer in LAYER_MAP.items():
        if name in parts_set:
            return layer
    return None


def detect_layer(path: pathlib.Path) -> str | None:
    """

    Args:
      path: pathlib.Path:
      path: pathlib.Path:

    Returns:

    """
    return detect_layer_from_parts(path.parts)


def layer_of(module_name: str) -> str:
    """

    Args:
      module_name: str:
      module_name: str:

    Returns:

    """
    if module_name.startswith("application.ports") or module_name == "application.ports":
        return "ports"
    detected = detect_layer_from_parts(module_name.split("."))
    return detected or "other"


def is_in_layer(path: pathlib.Path, layer_name: str) -> bool:
    """

    Args:
      path: pathlib.Path:
      layer_name: str:
      path: pathlib.Path:
      layer_name: str:

    Returns:

    """
    return layer_name in path.parts


def is_port_class(node: ast.ClassDef) -> bool:
    """

    Args:
      node: ast.ClassDef:
      node: ast.ClassDef:

    Returns:

    """
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {"Protocol", "ABC"}:
            return True
        if isinstance(base, ast.Attribute) and base.attr in {"Protocol", "ABC"}:
            return True
    return False


def collect_import_aliases(tree: ast.Module) -> dict[str, str]:
    """

    Args:
      tree: ast.Module:
      tree: ast.Module:

    Returns:

    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            base_module = node.module.split(".")[0]
            for alias in node.names:
                aliases[alias.asname or alias.name] = base_module
    return aliases


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


@dataclass
class Failure:
    """Reprezentuje naruszenie kontraktu architektonicznego."""

    category: str
    message: str
    file: pathlib.Path
    lineno: int | None = None
    is_type_checking: bool = False

    def __str__(self) -> str:
        """Reprezentacja tekstowa naruszenia."""
        suffix = " [TYPE_CHECKING hidden bypass]" if self.is_type_checking else ""
        relative = self.file.relative_to(ROOT)
        location = f"{relative}:{self.lineno}" if self.lineno is not None else str(relative)
        return f"[{self.category}] {self.message} - {location}{suffix}"


def check_forbidden_imports(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    stdlib_modules = set(sys.stdlib_module_names)
    explicitly_forbidden_stdlib = {"logging", "os", "random"}
    local_modules = get_local_module_names()
    allowed_bases = (stdlib_modules | local_modules) - explicitly_forbidden_stdlib

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        for ref in get_import_references(path, tree):
            if ref.base_module not in allowed_bases:
                failures.append(
                    Failure(
                        category="DOMAIN PURITY",
                        message=f"Non-stdlib import '{ref.base_module}' is forbidden in domain layer",
                        file=path,
                        lineno=ref.lineno,
                        is_type_checking=ref.is_type_checking,
                    )
                )


def check_determinism(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    forbidden_attr_calls = {
        "datetime.now",
        "datetime.utcnow",
        "random.choice",
        "random.randint",
        "random.random",
        "time.time",
        "uuid.uuid4",
    }
    forbidden_bare_calls = {"choice", "randint", "uuid4"}

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            call_name: str | None = None
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    call_name = f"{func.value.id}.{func.attr}"
                elif isinstance(func.value, ast.Attribute):
                    call_name = f"{func.value.attr}.{func.attr}"

            if call_name and call_name in forbidden_attr_calls:
                failures.append(
                    Failure(
                        category="DETERMINISM",
                        message=f"Non-deterministic call '{call_name}()' - use injected port",
                        file=path,
                        lineno=node.lineno,
                    )
                )

            if isinstance(func, ast.Name) and func.id in forbidden_bare_calls:
                failures.append(
                    Failure(
                        category="DETERMINISM",
                        message=f"Non-deterministic call '{func.id}()' - use injected port",
                        file=path,
                        lineno=node.lineno,
                    )
                )


def check_dataframe_in_domain(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "DataFrame":
                failures.append(
                    Failure(
                        category="DATAFRAME CONTRACT",
                        message="DataFrame usage detected - domain must use DTOs, not DataFrames",
                        file=path,
                        lineno=node.lineno,
                    )
                )
                break
            if isinstance(node, ast.Attribute) and node.attr == "DataFrame":
                failures.append(
                    Failure(
                        category="DATAFRAME CONTRACT",
                        message="DataFrame usage detected - domain must use DTOs, not DataFrames",
                        file=path,
                        lineno=node.lineno,
                    )
                )
                break


def check_env_access_in_application(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                call_name: str | None = None
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    call_name = f"{func.value.id}.{func.attr}"

                if call_name in {"os.getenv", "environ.get"}:
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message="os.getenv/environ.get in application - read env only in bootstrap",
                            file=path,
                            lineno=node.lineno,
                        )
                    )

                if isinstance(func, ast.Name) and func.id == "getenv":
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message="bare getenv() in application - read env only in bootstrap",
                            file=path,
                            lineno=node.lineno,
                        )
                    )

            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
                    failures.append(
                        Failure(
                            category="CONFIGURATION CONTRACT",
                            message="os.environ[] access in application - read env only in bootstrap",
                            file=path,
                            lineno=node.lineno,
                        )
                    )


def check_python_version_consistency(failures: list[Failure]) -> None:
    """

    Args:
      failures: list[Failure]:
      failures: list[Failure]:

    Returns:

    """
    versions: dict[str, str | None] = {
        ".python-version": None,
        "Dockerfile": None,
        "pyproject.toml": None,
    }

    python_version_file = ROOT / ".python-version"
    if python_version_file.exists():
        raw = python_version_file.read_text().strip()
        match = re.match(r"^(\d+\.\d+)", raw)
        if match:
            versions[".python-version"] = match.group(1)

    dockerfile = ROOT / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text()
        match = re.search(r"FROM python:(\d+\.\d+)", text)
        if match:
            versions["Dockerfile"] = match.group(1)

    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as file_obj:
            data = tomllib.load(file_obj)
        requires = data.get("project", {}).get("requires-python", "")
        match = re.search(r"(\d+\.\d+)", requires)
        if match:
            versions["pyproject.toml"] = match.group(1)

    found_versions = {name: value for name, value in versions.items() if value is not None}
    if len(found_versions) < 2:
        missing = [name for name, value in versions.items() if value is None]
        print(f"  [PYTHON VERSION] WARNING: Cannot verify - missing: {', '.join(missing)}")
        return

    if len(set(found_versions.values())) > 1:
        details = ", ".join(f"{name}={value}" for name, value in found_versions.items())
        failures.append(
            Failure(
                category="PYTHON VERSION CONSISTENCY",
                message=f"Version mismatch: {details} - all three must match",
                file=ROOT / "pyproject.toml",
            )
        )


def check_layer_dependencies(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        source_layer = detect_layer(path)
        if not source_layer:
            continue

        for ref in get_import_references(path, tree):
            if not is_local_module(ref.full_module):
                continue
            target_layer = layer_of(ref.full_module)
            if target_layer in FORBIDDEN_DEPENDENCIES.get(source_layer, set()):
                failures.append(
                    Failure(
                        category="LAYER VIOLATION",
                        message=f"{source_layer} must not depend on {target_layer} ('{ref.full_module}')",
                        file=path,
                        lineno=ref.lineno,
                        is_type_checking=ref.is_type_checking,
                    )
                )


def check_side_effects(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        import_aliases = collect_import_aliases(tree)

        for ref in get_import_references(path, tree):
            if ref.base_module in FORBIDDEN_SIDE_EFFECT_MODULES:
                failures.append(
                    Failure(
                        category="SIDE EFFECT",
                        message=f"Forbidden side-effect module '{ref.base_module}' in domain",
                        file=path,
                        lineno=ref.lineno,
                        is_type_checking=ref.is_type_checking,
                    )
                )

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            if isinstance(func, ast.Name):
                base_module = import_aliases.get(func.id)
                if func.id in FORBIDDEN_SIDE_EFFECT_FUNCTIONS or base_module in FORBIDDEN_SIDE_EFFECT_MODULES:
                    failures.append(
                        Failure(
                            category="SIDE EFFECT",
                            message=f"Forbidden side-effect function '{func.id}()' in domain",
                            file=path,
                            lineno=node.lineno,
                        )
                    )

            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                base_module = import_aliases.get(func.value.id, func.value.id)
                if base_module in FORBIDDEN_SIDE_EFFECT_MODULES:
                    failures.append(
                        Failure(
                            category="SIDE EFFECT",
                            message=f"Forbidden external call '{base_module}.{func.attr}()' in domain",
                            file=path,
                            lineno=node.lineno,
                        )
                    )


def collect_ports(files: list[pathlib.Path]) -> set[str]:
    """

    Args:
      files: list[pathlib.Path]:
      files: list[pathlib.Path]:

    Returns:

    """
    ports: set[str] = set()
    for path in files:
        if "ports" not in path.parts:
            continue

        tree = parse_file(path)
        if tree is None:
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and is_port_class(node):
                ports.add(node.name)

    return ports


def check_port_implementation(files: list[pathlib.Path], ports: set[str], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      ports: set[str]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      ports: set[str]:
      failures: list[Failure]:

    Returns:

    """
    if not ports:
        return

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        source_layer = detect_layer(path)
        if not source_layer:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue

            base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
            base_names.update(base.attr for base in node.bases if isinstance(base, ast.Attribute))

            implemented_ports = ports & base_names
            if not implemented_ports or source_layer == "ports":
                continue

            if source_layer != "infrastructure":
                failures.append(
                    Failure(
                        category="PORT VIOLATION",
                        message=(
                            "Only infrastructure may implement ports; "
                            f"class '{node.name}' implements {', '.join(sorted(implemented_ports))}"
                        ),
                        file=path,
                        lineno=node.lineno,
                    )
                )


def check_orm_usage(files: list[pathlib.Path], failures: list[Failure]) -> None:
    """

    Args:
      files: list[pathlib.Path]:
      failures: list[Failure]:
      files: list[pathlib.Path]:
      failures: list[Failure]:

    Returns:

    """
    for path in files:
        source_layer = detect_layer(path)
        if source_layer not in {"domain", "application", "ports"}:
            continue

        tree = parse_file(path)
        if tree is None:
            continue

        for ref in get_import_references(path, tree):
            if any(
                ref.full_module == prefix or ref.full_module.startswith(f"{prefix}.") for prefix in ORM_MODULE_PREFIXES
            ):
                failures.append(
                    Failure(
                        category="ORM VIOLATION",
                        message=f"ORM '{ref.full_module}' used outside infrastructure",
                        file=path,
                        lineno=ref.lineno,
                        is_type_checking=ref.is_type_checking,
                    )
                )


def build_dependency_graph(files: list[pathlib.Path]) -> dict[str, set[str]]:
    """

    Args:
      files: list[pathlib.Path]:
      files: list[pathlib.Path]:

    Returns:

    """
    graph: dict[str, set[str]] = defaultdict(set)

    for path in files:
        tree = parse_file(path)
        if tree is None:
            continue

        module_name = module_name_for_path(path)
        graph.setdefault(module_name, set())

        for ref in get_import_references(path, tree):
            if is_local_module(ref.full_module):
                graph[module_name].add(ref.full_module)
                graph.setdefault(ref.full_module, set())

    return dict(sorted((node, set(targets)) for node, targets in graph.items()))


def _canonicalize_cycle(cycle: list[str]) -> tuple[str, ...]:
    """

    Args:
      cycle: list[str]:
      cycle: list[str]:

    Returns:

    """
    core = cycle[:-1]
    if not core:
        return ()

    rotations = [tuple(core[index:] + core[:index]) for index in range(len(core))]
    reversed_core = list(reversed(core))
    rotations.extend(tuple(reversed_core[index:] + reversed_core[:index]) for index in range(len(reversed_core)))
    return min(rotations)


def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """

    Args:
      graph: dict[str:
      set[str]]:
      graph: dict[str:

    Returns:

    """
    visited: set[str] = set()
    stack: list[str] = []
    stack_index: dict[str, int] = {}
    seen_cycles: set[tuple[str, ...]] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        """

        Args:
          node: str:
          node: str:

        Returns:

        """
        visited.add(node)
        stack_index[node] = len(stack)
        stack.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in graph:
                continue
            if neighbor in stack_index:
                cycle = stack[stack_index[neighbor] :] + [neighbor]
                canonical = _canonicalize_cycle(cycle)
                if canonical and canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    cycles.append(list(canonical) + [canonical[0]])
                continue
            if neighbor not in visited:
                visit(neighbor)

        stack.pop()
        stack_index.pop(node, None)

    for node in graph:
        if node not in visited:
            visit(node)

    return cycles


def check_cycles(graph: dict[str, set[str]], failures: list[Failure]) -> None:
    """

    Args:
      graph: dict[str:
      set[str]]:
      failures: list[Failure]:
      graph: dict[str:
      failures: list[Failure]:

    Returns:

    """
    for cycle in detect_cycles(graph):
        failures.append(
            Failure(
                category="DEPENDENCY CYCLE",
                message=f"Cycle detected: {' -> '.join(cycle)}",
                file=ROOT / "pyproject.toml",
            )
        )


def export_graph_dot(graph: dict[str, set[str]], output: pathlib.Path = GRAPH_DOT_OUTPUT) -> pathlib.Path:
    """

    Args:
      graph: dict[str:
      set[str]]:
      output: pathlib.Path:  (Default value = GRAPH_DOT_OUTPUT)
      graph: dict[str:
      output: pathlib.Path:  (Default value = GRAPH_DOT_OUTPUT)

    Returns:

    """
    local_nodes = sorted(node for node in graph if is_local_module(node))
    grouped_nodes: dict[str, list[str]] = {layer: [] for layer in GRAPH_LAYER_ORDER}

    for node in local_nodes:
        grouped_nodes[layer_of(node)].append(node)

    with output.open("w", encoding="utf-8") as file_obj:
        file_obj.write("digraph G {\n")
        file_obj.write("  rankdir=LR;\n")
        file_obj.write("  graph [splines=true, overlap=false];\n")
        file_obj.write("  node [shape=box, style=filled, fontname=Helvetica];\n")
        file_obj.write("\n")

        for layer in GRAPH_LAYER_ORDER:
            nodes = grouped_nodes[layer]
            if not nodes:
                continue
            file_obj.write(f"  subgraph cluster_{layer} {{\n")
            file_obj.write(f'    label="{layer}";\n')
            file_obj.write("    color=gray60;\n")
            for node in nodes:
                color = LAYER_COLORS[layer_of(node)]
                file_obj.write(f'    "{node}" [fillcolor="{color}"];\n')
            file_obj.write("  }\n\n")

        for source, targets in sorted(graph.items()):
            if not is_local_module(source):
                continue
            for target in sorted(targets):
                if is_local_module(target):
                    file_obj.write(f'  "{source}" -> "{target}";\n')

        file_obj.write("}\n")

    return output


def export_graph_svg(graph: dict[str, set[str]], output: pathlib.Path = GRAPH_SVG_OUTPUT) -> pathlib.Path:
    """

    Args:
      graph: dict[str:
      set[str]]:
      output: pathlib.Path:  (Default value = GRAPH_SVG_OUTPUT)
      graph: dict[str:
      output: pathlib.Path:  (Default value = GRAPH_SVG_OUTPUT)

    Returns:

    """
    local_nodes = sorted(node for node in graph if is_local_module(node))
    grouped_nodes: dict[str, list[str]] = {layer: [] for layer in GRAPH_LAYER_ORDER}

    for node in local_nodes:
        grouped_nodes[layer_of(node)].append(node)

    if not local_nodes:
        output.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80"></svg>\n', encoding="utf-8")
        return output

    margin_x = 40
    margin_y = 40
    column_width = 280
    cluster_padding = 18
    node_width = 220
    node_height = 36
    node_gap = 18
    title_height = 22

    positions: dict[str, tuple[int, int]] = {}
    cluster_boxes: list[tuple[str, float, float, float, float]] = []
    max_height = 0.0

    for column_index, layer in enumerate(GRAPH_LAYER_ORDER):
        nodes = grouped_nodes[layer]
        if not nodes:
            continue

        cluster_x = margin_x + column_index * column_width
        cluster_y = margin_y
        node_x = cluster_x + cluster_padding
        node_y = cluster_y + title_height + cluster_padding

        for node in nodes:
            positions[node] = (node_x, node_y)
            node_y += node_height + node_gap

        cluster_height = (
            title_height + cluster_padding * 2 + len(nodes) * node_height + max(len(nodes) - 1, 0) * node_gap
        )
        cluster_boxes.append((layer, cluster_x, cluster_y, node_width + cluster_padding * 2, cluster_height))
        max_height = max(max_height, cluster_y + cluster_height)

    width = margin_x * 2 + max(len(GRAPH_LAYER_ORDER), 1) * column_width
    height = max(160.0, max_height + margin_y)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        "<defs>",
        '  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#5b6470" />',
        "  </marker>",
        "</defs>",
        '<rect width="100%" height="100%" fill="#f7f7f5" />',
    ]

    for layer, x, y, box_width, box_height in cluster_boxes:
        parts.append(
            f'<rect x="{x}" y="{y}" width="{box_width}" height="{box_height}" rx="16" fill="#ffffff" stroke="#b8bec7" stroke-width="1.5" />'
        )
        parts.append(
            f'<text x="{x + cluster_padding}" y="{y + 24}" font-family="Helvetica, Arial, sans-serif" font-size="15" font-weight="700" fill="#26313d">{html.escape(layer)}</text>'
        )

    for source, targets in sorted(graph.items()):
        if source not in positions:
            continue
        source_x, source_y = positions[source]
        start_x = source_x + node_width
        start_y = source_y + node_height / 2

        for target in sorted(targets):
            if target not in positions:
                continue
            target_x, target_y = positions[target]
            end_x = target_x
            end_y = target_y + node_height / 2
            control_offset = max(48.0, abs(end_x - start_x) * 0.35)
            path_d = (
                f"M {start_x:.1f} {start_y:.1f} "
                f"C {start_x + control_offset:.1f} {start_y:.1f}, "
                f"{end_x - control_offset:.1f} {end_y:.1f}, "
                f"{end_x:.1f} {end_y:.1f}"
            )
            parts.append(
                f'<path d="{path_d}" fill="none" stroke="#5b6470" stroke-width="1.6" opacity="0.8" marker-end="url(#arrow)" />'
            )

    for node in local_nodes:
        node_x, node_y = positions[node]
        color = LAYER_COLORS[layer_of(node)]
        label = html.escape(node)
        parts.append(
            f'<rect x="{node_x}" y="{node_y}" width="{node_width}" height="{node_height}" rx="10" fill="{color}" stroke="#7f8a96" stroke-width="1.2" />'
        )
        parts.append(
            f'<text x="{node_x + 12}" y="{node_y + 23}" font-family="Helvetica, Arial, sans-serif" font-size="12.5" fill="#1f2933">{label}</text>'
        )

    parts.append("</svg>\n")
    output.write_text("\n".join(parts), encoding="utf-8")
    return output


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run(config: AuditConfig) -> int:
    """

    Args:
      config: AuditConfig:
      config: AuditConfig:

    Returns:

    """
    failures: list[Failure] = []

    print("=== CONTRACT AUDIT ===")
    print()

    domain_files = collect_python_files(config.domain_paths)
    application_files = collect_python_files(config.application_paths)
    infrastructure_files = collect_python_files(_autodiscover(ROOT, "infrastructure"))
    interface_files = collect_python_files(_autodiscover(ROOT, "apps"))
    all_files = sorted({*domain_files, *application_files, *infrastructure_files, *interface_files})

    if not domain_files and not application_files:
        print("WARNING: No domain/ or application/ files found.")
        print("Configure paths in pyproject.toml [tool.audit] or check project structure.")
        print()

    print("Checking Python version consistency...")
    check_python_version_consistency(failures)

    if domain_files:
        print(f"Scanning domain/ ({len(domain_files)} files)...")
        check_forbidden_imports(domain_files, failures)
        check_determinism(domain_files, failures)
        check_dataframe_in_domain(domain_files, failures)
        check_side_effects(domain_files, failures)

    if application_files:
        print(f"Scanning application/ ({len(application_files)} files)...")
        check_determinism(application_files, failures)
        check_env_access_in_application(application_files, failures)

    if all_files:
        print(f"Scanning architecture graph ({len(all_files)} files)...")
        check_layer_dependencies(all_files, failures)
        check_orm_usage(all_files, failures)
        ports = collect_ports(all_files)
        check_port_implementation(all_files, ports, failures)
        graph = build_dependency_graph(all_files)
        check_cycles(graph, failures)
        if EXPORT_GRAPH:
            dot_output = export_graph_dot(graph)
            svg_output = export_graph_svg(graph)
            print(f"Exported dependency graph: {dot_output.relative_to(ROOT)}")
            print(f"Exported dependency graph: {svg_output.relative_to(ROOT)}")

    print()

    if failures:
        print(f"Audit FAILED - {len(failures)} violation(s):")
        print()
        for failure in failures:
            print(f"  x {failure}")
        print()
        return 1

    print("Audit PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run(AuditConfig.from_pyproject()))
