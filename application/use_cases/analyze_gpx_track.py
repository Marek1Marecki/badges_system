"""Przypadek użycia: Analiza pliku GPX i szukanie obiektów na trasie.

Zgodnie z US-C17: Wczytuje ślad w pamięci (bez zapisu), redukuje liczbę wierzchołków dla optymalizacji PostGIS i zwraca
propozycje zaliczeń w strefie buforowej.
"""

from application.dto.ascent_dto import GpxAnalysisResultDTO
from application.exceptions import UseCaseError
from application.ports.gpx_port import GpxParserPort
from application.ports.map_port import MapRepositoryPort


class AnalyzeGpxTrackUseCase:
    """Zwraca sugerowane daty i obiekty na podstawie analizy pliku przestrzennego."""

    # Tolerancja dla GPS i błędów kartograficznych (w metrach)
    BUFFER_METERS = 200.0

    def __init__(self, gpx_parser: GpxParserPort, map_repository: MapRepositoryPort) -> None:
        """Initialize the use case with required dependencies."""
        self._gpx_parser = gpx_parser
        self._map_repo = map_repository

    def execute(self, file_content: bytes) -> GpxAnalysisResultDTO:
        """Parsuje plik, generuje linię i odpytuje bazę GIS o sąsiadów.

        Args:
          file_content: Zawartość pliku GPX w bajtach.

        Returns:
          Wynik analizy z sugerowaną datą i pobliskimi szczytami.
        """
        # 1. Parsowanie i upraszczanie śladu
        line_wkt, suggested_date = self._gpx_parser.parse_gpx(file_content)

        if not line_wkt:
            raise UseCaseError("Nie udało się wyodrębnić ścieżki z dostarczonego pliku GPX.")

        # 2. Błyskawiczny strzał do PostGIS (Indeks GiST) z buforem
        nearby_objects = self._map_repo.get_objects_along_line(line_wkt, self.BUFFER_METERS)

        if not nearby_objects:
            raise UseCaseError(
                "Brak obiektów PTTK w promieniu 200m od wyznaczonej trasy. "
                "Upewnij się, że ślad mieści się w polskich górach."
            )

        return GpxAnalysisResultDTO(
            suggested_date=suggested_date,
            nearby_peaks=nearby_objects,
        )
