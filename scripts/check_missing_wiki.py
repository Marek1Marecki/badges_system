"""Skrypt kontrolny wyświetlający obiekty turystyczne bez linku do Wikipedii."""

import os
import sys

# Konfiguracja środowiska Django musi nastąpić PRZED jakimkolwiek importem z aplikacji
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()


def generate_report() -> None:
    """Wyszukuje i wyświetla obiekty bez linku do Wikipedii w kolejności dodania."""
    # Importy przeniesione do wnętrza funkcji rozwiązują błąd E402 (Ruff)
    # oraz gwarantują, że Django AppRegistry jest już gotowe.
    from django.db.models import Q

    from apps.badges.models import TouristObject

    objects_missing_wiki = TouristObject.objects.filter(
        Q(wikipedia_link__isnull=True) | Q(wikipedia_link__exact="")
    ).order_by("id")

    total_count = objects_missing_wiki.count()

    if total_count == 0:
        print("🎉 Doskonale! Wszystkie obiekty w bazie mają uzupełniony link do Wikipedii.")
        return

    print("=" * 70)
    print(f" RAPORT BRAKÓW: Obiekty bez linku do Wikipedii (Razem: {total_count})")
    print("=" * 70)

    for obj in objects_missing_wiki:
        osm_info = f"OSM: {obj.osm_id}" if obj.osm_id else "RĘCZNY (Brak OSM_ID)"
        code_info = f" | Kod: {obj.code}" if obj.code else ""

        print(f"[ID: {obj.id:04d}] {obj.name}[{obj.type}] -> {osm_info}{code_info}")

    print("-" * 70)
    print("Wskazówka: Możesz uzupełnić te linki ręcznie w panelu Admina.")


if __name__ == "__main__":
    generate_report()
