"""Adapter do komunikacji z API OpenStreetMap (Overpass)."""

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

from pydantic import BaseModel, Field

from apps.badges.models import OsmTypeMapping
from infrastructure.exceptions import InfrastructureException

logger = logging.getLogger(__name__)


class OsmAdapterError(InfrastructureException):
    """Błąd komunikacji z Overpass API."""


class OsmNodeDTO(BaseModel):
    """Struktura pojedynczego obiektu zwróconego przez Overpass API."""

    id: int
    type: str  # 'node', 'way', 'relation'
    lat: float | None = None
    lon: float | None = None
    tags: dict[str, str] = Field(default_factory=dict)

    # Dla obiektów typu way/relation Overpass z flagą 'out center'
    # zwraca środek ciężkości w słowniku 'center'
    center: dict[str, float] | None = None

    # NOWE: Odczyt metadanych z OSM
    version: int | None = None
    timestamp: datetime | None = None

    @property
    def latitude(self) -> float:
        """Bezpiecznie wyciąga szerokość geograficzną (dla node lub center)."""
        if self.lat is not None:
            return self.lat
        if self.center and "lat" in self.center:
            return self.center["lat"]
        raise ValueError(f"Brak współrzędnych dla obiektu {self.type}/{self.id}")

    @property
    def longitude(self) -> float:
        """Bezpiecznie wyciąga długość geograficzną."""
        if self.lon is not None:
            return self.lon
        if self.center and "lon" in self.center:
            return self.center["lon"]
        raise ValueError(f"Brak współrzędnych dla obiektu {self.type}/{self.id}")


class OverpassClient:
    """Klient HTTP do pobierania danych z OSM z mechanizmem Retry i Fallback."""

    OVERPASS_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; BadgeApp/1.0; +https://example.com)",
        "Accept": "application/json",
    }

    def fetch_object(self, osm_id: str, max_retries: int = 3) -> OsmNodeDTO:
        logger.info(f"\n--- ROZPOCZĘCIE POBIERANIA OSM ID: {osm_id} ---")

        try:
            osm_type, numeric_id = osm_id.strip().split("/")
        except ValueError as e:
            raise OsmAdapterError(f"Nieprawidłowy format osm_id: '{osm_id}'. Oczekiwano 'typ/id'.") from e

        if osm_type not in ("node", "way", "relation"):
            raise OsmAdapterError(f"Nieobsługiwany typ OSM: {osm_type}")

        out_modifier = "meta" if osm_type == "node" else "center meta"
        query = f"[out:json];{osm_type}({numeric_id});out {out_modifier};"

        # Kodujemy zapytanie, by było bezpieczne w URL
        encoded_query = urllib.parse.urlencode({"data": query})

        last_exception: Exception | None = None

        for attempt in range(max_retries):
            # UŻYWAMY GET: Doklejamy całe zapytanie bezpośrednio do URL-a
            base_url = self.OVERPASS_URLS[attempt % len(self.OVERPASS_URLS)]
            url = f"{base_url}?{encoded_query}"

            # Ważne: wysyłamy żądanie bez ciała (data=None) i bez jawnego wymuszania POST,
            # dzięki czemu urllib użyje domyślnej, nieblokowanej metody GET.
            req = urllib.request.Request(url, headers=self.HEADERS)  # noqa: S310

            try:
                # Limitujemy czas na odpowiedź do 8 sekund. Serwer francuski
                # od razu wyrzuci timeout, a my nie zablokujemy workera!
                with urllib.request.urlopen(req, timeout=30.0) as response:  # noqa: S310
                    response_body = response.read().decode("utf-8")
                    logger.info("SUKCES! Pomyślnie pobrano dane.")
                    response_data = json.loads(response_body)
                    break

            except urllib.error.HTTPError as e:
                last_exception = e
                error_body = e.read().decode("utf-8", errors="replace")
                logger.warning(f"Serwer odrzucił żądanie. Błąd {e.code}")

                if e.code in (400, 404):
                    raise OsmAdapterError(f"Odrzucono zapytanie ({e.code}): {error_body[:100]}") from e

                if attempt < max_retries - 1:
                    time.sleep(1.0 * (2**attempt))
                    continue

            except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
                last_exception = e
                logger.error(f"Błąd sieci/parsowania/timeout: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (2**attempt))
                    continue
        else:
            raise OsmAdapterError(
                f"Nie udało się połączyć z Overpass API po {max_retries} próbach. Ostatni błąd: {last_exception}"
            )

        if not response_data:
            raise OsmAdapterError(f"Brak danych z OSM dla obiektu {osm_id}.")

        elements = response_data.get("elements", [])
        if not elements:
            raise OsmAdapterError(f"Obiekt {osm_id} nie został znaleziony w OSM.")

        try:
            return OsmNodeDTO.model_validate(elements[0])
        except Exception as e:
            raise OsmAdapterError(f"Błąd parsowania danych z OSM: {e}") from e

    def fetch_multiple_objects(self, osm_ids: list[str], max_retries: int = 3) -> dict[str, OsmNodeDTO]:
        """Pobiera zbiorczo obiekty z OSM (Bulk Fetching) dla optymalizacji ruchu."""
        if not osm_ids:
            return {}

        queries = []
        for osm_id in osm_ids:
            try:
                osm_type, num_id = osm_id.strip().split("/")
                queries.append(f"{osm_type}({num_id});")
            except ValueError:
                continue

        if not queries:
            return {}

        query = f"[out:json];({''.join(queries)});out center meta;"

        import urllib.parse
        import urllib.request

        # Kodujemy zapytanie do użycia w adresie URL (dla metody GET)
        encoded_query = urllib.parse.urlencode({"data": query})

        last_exception: Exception | None = None
        response_data = None

        for attempt in range(max_retries):
            # UŻYWAMY GET (doklejamy zapytanie do URL) JAK W POJEDYNCZYM POBIERANIU
            base_url = self.OVERPASS_URLS[attempt % len(self.OVERPASS_URLS)]
            url = f"{base_url}?{encoded_query}"

            # Wysyłamy żądanie bez ciała (data=None) i bez jawnego wymuszania POST,
            # by uniknąć zaporowych błędów 406.
            req = urllib.request.Request(url, headers=self.HEADERS)  # noqa: S310

            try:
                with urllib.request.urlopen(req, timeout=40.0) as response:  # noqa: S310
                    import json

                    response_body = response.read().decode("utf-8")
                    response_data = json.loads(response_body)
                    logger.info("SUKCES! Pomyślnie pobrano paczkę danych.")
                    break

            except urllib.error.HTTPError as e:
                last_exception = e
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Błąd przy masowym pobieraniu OSM (próba {attempt + 1}): HTTP {e.code}")

                if e.code < 500:
                    if e.code == 429:  # Zbyt wiele zapytań -> ignorujemy i ponawiamy
                        pass
                    elif e.code in (400, 404):
                        raise OsmAdapterError(f"Odrzucono zapytanie masowe ({e.code})") from e

                if attempt < max_retries - 1:
                    import time

                    time.sleep(1.0 * (2**attempt))
                    continue

            except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
                last_exception = e
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Błąd sieci/timeout przy masowym pobieraniu: {str(e)}")
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1.0 * (2**attempt))
                    continue
        else:
            raise OsmAdapterError(f"Wyczerpano {max_retries} prób masowego pobierania. Ostatni błąd: {last_exception}")

        if not response_data:
            raise OsmAdapterError("Brak danych zwrotnych z OSM dla masowego zapytania.")

        elements = response_data.get("elements", [])
        results = {}

        for el in elements:
            try:
                dto = OsmNodeDTO.model_validate(el)
                key = f"{dto.type}/{dto.id}"
                results[key] = dto
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Pominięto uszkodzony element z OSM w bulk fetch: {e}")

        return results


class OsmDataExtractor:
    """Tłumaczy surowe dane OSM na format akceptowany przez modele Django."""

    # Twarda lista kluczy OSM, które uznajemy za określające "Typ obiektu"
    # Ignorujemy całą resztę śmieci (name, ele, source, wikipedia itp.)
    CLASSIFYING_KEYS = {"natural", "tourism", "historic", "waterway", "man_made", "building", "tower:type"}

    @staticmethod
    def extract_name(tags: dict[str, str]) -> str | None:
        """Pobiera najlepszą dostępną nazwę."""
        if "name:pl" in tags:
            return tags["name:pl"]
        if "name" in tags:
            return tags["name"]
        if "alt_name" in tags:
            return tags["alt_name"]
        return None

    @staticmethod
    def extract_alt_name(tags: dict[str, str], primary_name: str | None) -> str | None:
        """Pobiera alternatywną nazwę z OSM (uwzględniając tagi językowe), unikając duplikacji."""
        # Szukamy najpierw polskiej alternatywy, a potem ogólnej
        alt = tags.get("alt_name:pl") or tags.get("alt_name")
        if alt and alt != primary_name:
            return alt
        return None

    @staticmethod
    def extract_altitude(tags: dict[str, str]) -> int | None:
        """Bezpiecznie parsuje wysokość z tagu 'ele'."""
        ele_str = tags.get("ele")
        if not ele_str:
            return None

        match = re.search(r"[-+]?\d+", ele_str)
        if match:
            return int(match.group())
        return None

    @staticmethod
    def determine_type(tags: dict[str, str]) -> tuple[str | None, list[str]]:
        """
        Przeszukuje klasyfikujące tagi OSM.
        Zwraca krotkę: (Zmapowany Typ lub None, Lista nowo utworzonych wpisów do Inboxu).
        """
        found_type = None
        newly_created_mappings = []

        for key in OsmDataExtractor.CLASSIFYING_KEYS:
            if key in tags:
                val = tags[key]

                # Używamy get_or_create, by pobrać wpis z bazy lub utworzyć nowy, pusty
                mapping, created = OsmTypeMapping.objects.get_or_create(
                    osm_key=key, osm_value=val, defaults={"target_type": "", "is_ignored": False}
                )

                if created:
                    newly_created_mappings.append(f"{key}={val}")

                # Jeśli jeszcze nie znaleźliśmy typu, a to mapowanie ma jakiś przypisany
                # (i nie jest ignorowane), to przyjmujemy go jako typ obiektu!
                if not found_type and not mapping.is_ignored and mapping.target_type:
                    found_type = mapping.target_type

        return str(found_type) if found_type else None, newly_created_mappings

    @staticmethod
    def extract_wikipedia_link(tags: dict[str, str]) -> str | None:
        """Pobiera i formatuje referencję do Wikipedii z tagów OSM."""

        # 1. Szukamy tagów wiki. Faworyzujemy bezpośrednie polskie linki,
        # potem ogólny tag 'wikipedia' (który często ma w sobie przedrostek pl:),
        # a na koniec inne języki (np. dla obiektów w 100% po stronie czeskiej).
        wiki_ref = None
        if "wikipedia:pl" in tags:
            wiki_ref = f"pl:{tags['wikipedia:pl']}"
        elif "wikipedia" in tags:
            wiki_ref = tags["wikipedia"]
        elif "wikipedia:sk" in tags:
            wiki_ref = f"sk:{tags['wikipedia:sk']}"
        elif "wikipedia:cs" in tags:
            wiki_ref = f"cs:{tags['wikipedia:cs']}"

        if not wiki_ref:
            return None

        # 2. OSM formatuje to zazwyczaj jako 'język:Tytuł Hasła' (np. 'pl:Rysy')
        try:
            lang, title = wiki_ref.split(":", 1)
            # Trzeba podmienić spacje na podkreślenia w adresie URL
            formatted_title = title.strip().replace(" ", "_")
            return f"https://{lang.strip().lower()}.wikipedia.org/wiki/{formatted_title}"
        except ValueError:
            # Jeśli format w OSM był niestandardowy (bez dwukropka),
            # próbujemy zbudować chociaż polski link jako domyślny fallback
            formatted_title = wiki_ref.strip().replace(" ", "_")
            return f"https://pl.wikipedia.org/wiki/{formatted_title}"

    @staticmethod
    def extract_start_date(tags: dict[str, str]) -> date | None:
        """Próbuje bezpiecznie wyciągnąć i sformatować datę powstania obiektu z tagów OSM."""
        start_str = tags.get("start_date")
        if not start_str:
            return None

        # Używamy wyrażeń regularnych, by wyłowić najpopularniejsze, twarde formaty z OSM
        import re

        # Przypadek 1: Pełna data YYYY-MM-DD
        match_full = re.match(r"^(\d{4})-(\d{2})-(\d{2})", start_str)
        if match_full:
            try:
                return date(int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3)))
            except ValueError:
                pass  # Błędne dni/miesiące

        # Przypadek 2: Rok i miesiąc YYYY-MM (Zgadywanie: 1 dzień miesiąca)
        match_month = re.match(r"^(\d{4})-(\d{2})", start_str)
        if match_month:
            try:
                return date(int(match_month.group(1)), int(match_month.group(2)), 1)
            except ValueError:
                pass

        # Przypadek 3: Sam rok YYYY (Zgadywanie: 1 stycznia)
        # Często poprzedzone znakami typu 'C19', '~1890'. Wyciągamy pierwszą 4-cyfrową liczbę.
        match_year = re.search(r"(\d{4})", start_str)
        if match_year:
            return date(int(match_year.group(1)), 1, 1)

        # Jeśli format był całkowicie opisowy (np. "wiosna 1920", "XIX wiek"), poddajemy się.
        # Wymaga to ludzkiego oka w panelu Admina.
        return None
