"""Adapter przestrzenny do parsowania śladów GPX.

Wykorzystuje wyłącznie bibliotekę standardową (ElementTree) oraz GeoDjango. Zgodnie z ADR-002 ukrywa operacje GEOS przed
warstwą aplikacji, oddając czysty tekst WKT (Well-Known Text).
"""

from datetime import date

import defusedxml.ElementTree as ET
from django.contrib.gis.geos import LineString

from application.ports.gpx_port import GpxParserPort
from infrastructure.exceptions import InfrastructureException


class DjangoGpxParser(GpxParserPort):
    """Parser plików GPX korzystający z biblioteki Django."""

    def parse_gpx(self, file_content: bytes) -> tuple[str | None, date | None]:
        """

        Args:
          file_content: bytes:
          file_content: bytes:

        Returns:

        """
        try:
            # Używamy bezpiecznej wersji chroniącej przed atakami DoS na pamięć RAM
            root = ET.fromstring(file_content)
        except Exception as e:  # <--- ZMIANA: Łapiemy wszystkie błędy parsera i defusedxml
            raise InfrastructureException("Nieprawidłowy plik lub podejrzana struktura XML (Atak).") from e

        # Standard GPX używa namespaców. Wyszukujemy elementy niezależnie od namespace'u {*}.
        trkpts = root.findall(".//{*}trkpt")

        # ... (reszta metody z pętlą 'for pt in trkpts:' pozostaje DOKŁADNIE BEZ ZMIAN!) ...
        if not trkpts:
            raise InfrastructureException("Plik GPX nie zawiera ścieżki z punktami (trkpt).")

        points = []
        for pt in trkpts:
            try:
                lat = float(pt.attrib["lat"])
                lon = float(pt.attrib["lon"])
                points.append((lon, lat))  # GEOS używa formatu (X, Y) -> (Lon, Lat)
            except (KeyError, ValueError):
                continue

        if len(points) < 2:
            raise InfrastructureException("Ślad GPX jest za krótki (mniej niż 2 punkty).")

        # Optymalizacja (Line Simplification): Budujemy linię i upraszczamy ją o ok. 10 metrów.
        # Drastycznie redukuje to ilość wierzchołków dla ST_DWithin chroniąc PostGIS!
        line = LineString(points, srid=4326)
        simplified_line = line.simplify(0.0001, preserve_topology=False)

        # Wyciąganie daty wycieczki (Sugerujemy na podstawie pierwszego punktu trasy)
        suggested_date = None
        time_node = trkpts[0].find(".//{*}time")
        if time_node is not None and time_node.text:
            try:
                # Oczekiwany format w GPX: 2024-08-14T10:30:00Z
                suggested_date = date.fromisoformat(time_node.text[:10])
            except ValueError:
                pass

        return simplified_line.wkt, suggested_date
