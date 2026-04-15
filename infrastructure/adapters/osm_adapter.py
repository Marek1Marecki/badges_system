"""Adapter do komunikacji z API OpenStreetMap (Overpass)."""

import json
import re
import time
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from apps.badges.models import OsmTypeMapping
from infrastructure.exceptions import InfrastructureException


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

    # Skrócona i najbardziej niezawodna lista publicznych węzłów Overpass w Europie.
    OVERPASS_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",  # Oficjalny serwer klastrowany
    ]

    # Wymagany przez netykietę OpenStreetMap "User-Agent"
    # Bez niego wiele serwerów zwraca 403 Forbidden dla skryptów.
    HEADERS = {"User-Agent": "BadgeSystem/1.0 (Contact: admin@example.com)", "Accept": "application/json"}

    def fetch_object(self, osm_id: str, max_retries: int = 3) -> OsmNodeDTO:
        try:
            osm_type, numeric_id = osm_id.strip().split("/")
        except ValueError as e:
            raise OsmAdapterError(f"Nieprawidłowy format osm_id: '{osm_id}'. Oczekiwano 'typ/id'.") from e

        if osm_type not in ("node", "way", "relation"):
            raise OsmAdapterError(f"Nieobsługiwany typ OSM: {osm_type}")

        query = f"""
        [out:json];
        {osm_type}({numeric_id});
        out center meta;
        """

        last_exception = None

        for attempt in range(max_retries):
            url = self.OVERPASS_URLS[attempt % len(self.OVERPASS_URLS)]

            try:
                # Wysłanie zapytania z jawnym User-Agent'em, co rozwiązuje problem 403.
                with httpx.Client(timeout=25.0, headers=self.HEADERS) as client:
                    # Overpass API przyjmuje skrypty również jako POST w urlencode
                    response = client.post(url, data={"data": query})

                    response.raise_for_status()
                    data = response.json()
                    break

            except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
                last_exception = e

                # Zabezpieczenie przed 40x.
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    # Bardzo restrykcyjne API OSM czasem oddaje 429 Too Many Requests
                    if e.response.status_code == 429:
                        # W przypadku "429 Too Many Requests" traktujemy to jako błąd
                        # infrastruktury przejściowy (możemy poczekać i ponowić).
                        pass
                    else:
                        raise OsmAdapterError(f"Błąd klienta OSM ({e.response.status_code}): {e}") from e

                # Jeśli jeszcze nie osiągnięto max_retries - ponów.
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (2**attempt))
                    continue
        else:
            raise OsmAdapterError(
                f"Nie udało się połączyć z Overpass API po {max_retries} próbach. Ostatni błąd: {last_exception}"
            )

        elements = data.get("elements", [])
        if not elements:
            raise OsmAdapterError(f"Obiekt {osm_id} nie został znaleziony w OSM.")

        try:
            return OsmNodeDTO.model_validate(elements[0])
        except Exception as e:
            raise OsmAdapterError(f"Błąd parsowania danych z OSM: {e}") from e


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
