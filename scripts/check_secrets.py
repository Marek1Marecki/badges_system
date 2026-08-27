"""Weryfikacja obecności sekretów w środowisku.

Skrypt sprawdza, czy wszystkie klucze zdefiniowane w .env.example znajdują się w lokalnym pliku .env (lub w zmiennych
środowiskowych OS). Zgodnie z 10-secrets-management.md.
"""

import os
import sys
from pathlib import Path


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


if __name__ == "__main__":
    check_secrets()
