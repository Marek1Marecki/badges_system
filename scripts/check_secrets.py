"""Weryfikacja obecności sekretów w środowisku.

Skrypt sprawdza, czy wszystkie klucze zdefiniowane w .env.example znajdują się w lokalnym
pliku .env (lub w zmiennych środowiskowych OS). Zgodnie z 10-secrets-management.md.

Dodatkowo skanuje repozytorium pod kątem zamienionych sekretów (AUDYT-135).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Wzorce wrażliwych danych — proste, szerokie dopasowanie (AUDYT-135).
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google OAuth secret", re.compile(r"GOCSPX-[A-Za-z0-9_-]+")),
    ("Django SECRET_KEY (production-like)", re.compile(r"^[A-Za-z0-9]{32,}$", re.MULTILINE)),
    ("Generic API key", re.compile(r"(api[_-]?key|secret|token|password)\s*=\s*\S+", re.IGNORECASE)),
]

# Pliki/ścieżki wykluczone z skanowania sekretów.
SENSITIVE_FILES = {".env.prod", ".env.preprod.secrets", ".env.old", ".env.dev.backup_20260716"}


def scan_for_committed_secrets() -> list[str]:
    """Skanuje pliki .env* pod kątem wycieków sekretów (AUDYT-135)."""
    findings: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent

    for env_file in repo_root.glob(".env*"):
        if env_file.name == ".env.example" or env_file.is_dir():
            continue
        if env_file.name in SENSITIVE_FILES:
            # Te pliki są świadomie chronione .gitignore lub szyfrowane.
            continue
        # Skip files that are git-ignored (not committed to repository).
        result = subprocess.run(
            ["git", "check-ignore", str(env_file)],  # noqa: S607
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            continue

        content = env_file.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content[: match.start()].count("\n") + 1
                findings.append(f"{env_file.name}:{line_no} — {label}: {match.group()[:20]}...")

    return findings


def check_secrets() -> None:
    """Skanuje kod w poszukiwaniu potencjalnych sekretów."""
    example_path = Path(".env.example")
    env_path = Path(".env")

    if not example_path.exists():
        print("Brak pliku .env.example. Pomijam sprawdzanie.")
        sys.exit(0)

    # 1. Odczytanie wymaganych kluczy z .env.example
    required_keys = set()
    with open(example_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                required_keys.add(line.split("=")[0].strip())

    # 2. Odczytanie fizycznych kluczy z lokalnego pliku .env
    present_keys = set()
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    present_keys.add(line.split("=")[0].strip())

    # 3. Sprawdzenie, czy klucze nie zostały wstrzyknięte z zewnątrz (np. w CI/CD)
    for key in required_keys:
        if os.getenv(key):
            present_keys.add(key)

    # 4. Werdykt
    missing = sorted(required_keys - present_keys)

    if missing:
        print(f"Brakujące sekrety w pliku .env (lub zmiennych środowiskowych): {', '.join(missing)}")
        sys.exit(1)

    print(f"✅ Sukces: Wszystkie {len(required_keys)} wymagane sekrety są obecne.")

    # 5. Scan for committed secrets (AUDYT-135)
    committed = scan_for_committed_secrets()
    if committed:
        print("\n⚠️  Wykryto potencjalne sekrety w zatwierdzonych plikach .env*:")
        for finding in committed:
            print(f"   - {finding}")  # pragma: allowlist secret — finding is masked ([:20] chars, see scan_for_committed_secrets)
        print("\n💡 Rozważ: 1) usunięcie sekretów z historii Git, 2) wdrożenie SOPS dla .env.prod")
        sys.exit(1)


if __name__ == "__main__":
    check_secrets()
