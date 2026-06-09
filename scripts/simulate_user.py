"""Skrypt symulujący weryfikację odznaki turysty (Integration Test)."""

import os
import sys
from datetime import date

# 1. Inicjalizacja środowiska Django (niezbędne, by użyć ORM w skrypcie)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()


def run_simulation() -> None:
    """Uruchamia symulację użytkowników zdobywających odznakę."""
    # Importy wewnątrz funkcji rozwiązują błąd E402 (Ruff) i gwarantują,
    # że Django jest gotowe do udostępnienia modeli aplikacji.
    from application.dto.ascent_dto import AscentInputDTO
    from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
    from application.use_cases.verify_badge import VerifyBadgeUseCase
    from apps.badges.models import TouristObject
    from infrastructure.adapters.persistence.django_badge_repo import DjangoBadgeRepository

    # Pobieramy ID obiektów z bazy (TouristObject), by dopasować logi turysty
    try:
        babia = TouristObject.objects.filter(name__icontains="Babia").first()
        skrzyczne = TouristObject.objects.filter(name__icontains="Skrzyczne").first()

        if not babia or not skrzyczne:
            print("Najpierw dodaj Babią Górę i Skrzyczne w panelu Admina!")
            return

        babia_id = babia.id
        skrzyczne_id = skrzyczne.id

    except Exception as e:
        print(f"Wystąpił błąd przy pobieraniu obiektów: {e}")
        return

    print("--- ROZPOCZĘCIE WERYFIKACJI ---")

    # Tworzymy nasz port i wstrzykujemy go do Use Case'u
    repo = DjangoBadgeRepository()
    use_case = VerifyBadgeUseCase(repository=repo)

    # UWAGA: Upewnij się, że masz w bazie Odznakę "KPB" i Wersję "v2024"
    # do której w panelu Admina (w Stopniu!) przypiąłeś Babią Górę i Skrzyczne.

    # ==========================================
    # SCENARIUSZ 1: Turysta poprawny
    # ==========================================
    print(f"\n[Scenariusz 1] Jan Kowalski: Wszystko poprawnie (Babia ID: {babia_id}, Skrzyczne ID: {skrzyczne_id})")
    request_jan = VerifyBadgeRequestDTO(
        badge_code="KPB",
        version_code="v2024",
        ascents=[
            AscentInputDTO(peak_id=babia_id, ascent_date=date(2023, 5, 10)),
            AscentInputDTO(peak_id=skrzyczne_id, ascent_date=date(2024, 8, 15)),
        ],
    )

    try:
        result_jan = use_case.execute(request_jan)
        print(f"Wynik Jana: {result_jan}")
    except Exception as e:
        print(f"Błąd uruchamiania scenariusza 1: {e}")

    # ==========================================
    # SCENARIUSZ 2: Turysta narusza reguły (Narty i brak obiektu)
    # ==========================================
    print("\n[Scenariusz 2] Anna Nowak: Narty i brak 1 obiektu")
    request_anna = VerifyBadgeRequestDTO(
        badge_code="KPB",
        version_code="v2024",
        ascents=[
            # Anna weszła tylko na Babią
            AscentInputDTO(peak_id=babia_id, ascent_date=date(2024, 1, 15)),
        ],
    )

    try:
        result_anna = use_case.execute(request_anna)
        print(f"Wynik Anny: {result_anna}")
    except Exception as e:
        print(f"Błąd uruchamiania scenariusza 2: {e}")


if __name__ == "__main__":
    run_simulation()
