"""Poligon doświadczalny symulujący zachowanie turysty (Faza C)."""

import os
import sys

# Inicjalizacja Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO  # noqa: E402
from bootstrap import get_container  # noqa: E402


def run_simulation() -> None:
    """Przykładowe wywołanie weryfikacji przez kontener DI."""
    print("=" * 60)
    print("SYMULATOR FAZY C: WERYFIKACJA ODZNAKI")
    print("=" * 60)

    # 1. Pobieramy gotowy, okablowany Use Case z kontenera
    container = get_container()
    verify_badge_use_case = container["verify_badge"]

    # 2. Tworzymy żądanie dla hipotetycznego turysty o ID = 1
    dto = VerifyBadgeRequestDTO(profile_id=1, badge_code="KGP", cycle_number=1)

    print(f"Wysyłam żądanie weryfikacji: {dto}")

    # 3. Wykonanie weryfikacji
    try:
        result = verify_badge_use_case.execute(dto)
        print(f"\n✅ WYNIK WERYFIKACJI:\n{result}")
    except Exception as e:
        # Błąd jest jak najbardziej spodziewany, jeśli w bazie nie masz usera o ID 1
        # lub turysta ten nie rozpoczął jeszcze zdobywania KGP!
        print(f"\n⚠️ PRZERWANO (Spodziewany wyjątek biznesowy):\n{e}")

    print("=" * 60)


if __name__ == "__main__":
    run_simulation()
