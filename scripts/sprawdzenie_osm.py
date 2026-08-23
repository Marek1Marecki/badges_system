"""Skrypt testowy do sprawdzania połączenia z Overpass API."""

import os
import sys

# Konfiguracja środowiska Django przed importami modeli aplikacji
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()


def test_kremenaros() -> None:
    """Testuje pobieranie i ekstrakcję danych z OSM dla punktu granicznego."""
    # Importy wewnątrz funkcji rozwiązują błąd E402 i gwarantują,
    # że Django jest gotowe do udostępnienia np. ChoiceType dla modeli.
    from infrastructure.adapters.osm_adapter import OsmDataExtractor, OverpassClient

    client = OverpassClient()
    print("Pobieram Kremenaros z OSM...")
    # node/477984782 to Kremenaros na trójstyku
    osm_data = client.fetch_object("way/27918182")

    print("\n--- SUROWE TAGI Z OSM (Do Data Lake) ---")
    print(f"Liczba tagów: {len(osm_data.tags)}")
    print(f"Oryginalna nazwa: {osm_data.tags.get('name')}")
    print(f"Słowacka nazwa: {osm_data.tags.get('name:sk')}")

    print("\n--- WYEKSTRAHOWANE DANE (Do bazy Django) ---")
    print(f"Nazwa (Polska faworyzowana): {OsmDataExtractor.extract_name(osm_data.tags)}")
    print(f"Wysokość: {OsmDataExtractor.extract_altitude(osm_data.tags)} m")
    print(f"Typ Obiektu: {OsmDataExtractor.determine_type(osm_data.tags)}")
    print(f"Współrzędne (Point): {osm_data.longitude}, {osm_data.latitude}")


if __name__ == "__main__":
    test_kremenaros()
