"""Skrypt kontrolny wyświetlający obiekty, które nie są przypięte do żadnej odznaki."""

import os
import sys

# Konfiguracja środowiska Django musi nastąpić PRZED jakimkolwiek importem z aplikacji
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()


def generate_report() -> None:
    """Wyszukuje i wyświetla obiekty bez przypisanych odznak w kolejności dodania."""
    from apps.badges.models import TouristObject

    # Filtrujemy obiekty, do których nie odnosi się żadna wersja odznaki
    # Wykorzystujemy magię Django ORM: szukamy pustej odwrotnej relacji M2M
    orphans = TouristObject.objects.filter(badgeversionmodel__isnull=True).order_by("id")

    total_count = orphans.count()

    if total_count == 0:
        print("🎉 Doskonale! Wszystkie obiekty w bazie są przypięte do co najmniej jednej odznaki.")
        return

    print("=" * 70)
    print(f" RAPORT SIEROT: Obiekty bez przypisanej odznaki (Razem: {total_count})")
    print("=" * 70)

    for obj in orphans:
        osm_info = f"OSM: {obj.osm_id}" if obj.osm_id else "RĘCZNY (Brak OSM_ID)"
        # Używamy getattr bezpiecznie, na wypadek gdybyś nie dodał kiedyś is_active
        active_status = "" if getattr(obj, "is_active", True) else " [ZOBIEKT ZNISZCZONY]"

        print(f"[ID: {obj.id:04d}] {obj.name} [{obj.type}]{active_status} -> {osm_info}")

    print("-" * 70)
    print("Wskazówka: Możesz je przypisać do odznaki, usunąć, lub oznaczyć is_active=False.")


if __name__ == "__main__":
    generate_report()
