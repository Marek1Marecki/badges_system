"""Port dla parsera plików przestrzennych.

Chroni przed wyciekiem GIS do Domeny.
"""

from datetime import date
from typing import Protocol


class GpxParserPort(Protocol):
    """Port dla parsera plików GPX."""

    def parse_gpx(self, file_content: bytes) -> tuple[str | None, date | None]:
        """Przetwarza plik GPX.

        Zwraca: (Geometria w formacie WKT, sugerowana data wycieczki).
        """
        ...
