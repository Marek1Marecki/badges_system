"""Tests for AnalyzeGpxTrackUseCase."""

from datetime import date

import pytest

from application.dto.ascent_dto import GpxAnalysisResultDTO
from application.exceptions import UseCaseError
from application.use_cases.analyze_gpx_track import AnalyzeGpxTrackUseCase


class MockGpxParser:
    def parse_gpx(self, file_content):
        return ("LINESTRING(0 0, 1 1)", date(2023, 1, 1))


class MockGpxParserInvalid:
    def parse_gpx(self, file_content):
        return (None, None)


class MockGpxParserEmpty:
    def parse_gpx(self, file_content):
        return ("", None)


class MockMapRepo:
    def get_objects_along_line(self, line_wkt, buffer_meters):
        return [{"id": 1, "name": "peak1"}, {"id": 2, "name": "peak2"}]


class MockMapRepoEmpty:
    def get_objects_along_line(self, line_wkt, buffer_meters):
        return []


class TestAnalyzeGpxTrackUseCase:
    """Test AnalyzeGpxTrackUseCase."""

    def test_execute_with_valid_gpx_content(self):
        """Test execute with valid GPX content."""
        gpx_parser = MockGpxParser()
        map_repo = MockMapRepo()

        use_case = AnalyzeGpxTrackUseCase(gpx_parser, map_repo)
        result = use_case.execute(b"valid_gpx_content")

        assert isinstance(result, GpxAnalysisResultDTO)
        assert result.suggested_date == date(2023, 1, 1)
        assert result.nearby_peaks == [{"id": 1, "name": "peak1"}, {"id": 2, "name": "peak2"}]

    def test_execute_with_invalid_gpx_content(self):
        """Test execute with invalid GPX content raises UseCaseError."""
        gpx_parser = MockGpxParserInvalid()
        map_repo = MockMapRepoEmpty()

        use_case = AnalyzeGpxTrackUseCase(gpx_parser, map_repo)

        with pytest.raises(UseCaseError) as exc_info:
            use_case.execute(b"invalid_gpx_content")

        assert "Nie udało się wyodrębnić ścieżki z dostarczonego pliku GPX" in str(exc_info.value)

    def test_execute_with_empty_line_wkt(self):
        """Test execute with empty line WKT raises UseCaseError."""
        gpx_parser = MockGpxParserEmpty()
        map_repo = MockMapRepoEmpty()

        use_case = AnalyzeGpxTrackUseCase(gpx_parser, map_repo)

        with pytest.raises(UseCaseError) as exc_info:
            use_case.execute(b"empty_gpx_content")

        assert "Nie udało się wyodrębnić ścieżki z dostarczonego pliku GPX" in str(exc_info.value)

    def test_execute_calls_map_repo_with_buffer(self):
        """Test that execute calls map repo with correct buffer distance."""
        gpx_parser = MockGpxParser()
        map_repo = MockMapRepo()

        use_case = AnalyzeGpxTrackUseCase(gpx_parser, map_repo)
        use_case.execute(b"valid_gpx_content")

        # Verify buffer is used
        assert use_case.BUFFER_METERS == 200.0

    def test_execute_with_no_nearby_objects(self):
        """AUDYT-092: pusta lista → UseCaseError ( nie cichy 200 )."""
        gpx_parser = MockGpxParser()
        map_repo = MockMapRepoEmpty()

        use_case = AnalyzeGpxTrackUseCase(gpx_parser, map_repo)

        with pytest.raises(UseCaseError, match="Brak obiektów PTTK"):
            use_case.execute(b"valid_gpx_content")

    def test_buffer_meters_constant(self):
        """Test that BUFFER_METERS constant is set correctly."""
        assert AnalyzeGpxTrackUseCase.BUFFER_METERS == 200.0
