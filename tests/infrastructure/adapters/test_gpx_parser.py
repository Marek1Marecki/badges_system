"""Tests for GPX parser adapter."""

from datetime import date

import pytest

from infrastructure.adapters.gpx_parser import DjangoGpxParser
from infrastructure.exceptions import InfrastructureException


class TestDjangoGpxParser:
    """Test suite for DjangoGpxParser."""

    def test_parse_valid_gpx(self):
        """Test parsing a valid GPX file with track points."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="50.0647" lon="19.9450">
        <time>2024-08-14T10:30:00Z</time>
      </trkpt>
      <trkpt lat="50.0650" lon="19.9455">
        <time>2024-08-14T10:31:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        wkt, suggested_date = parser.parse_gpx(gpx_content)

        assert wkt is not None
        assert wkt.startswith("LINESTRING")
        assert suggested_date == date(2024, 8, 14)

    def test_parse_gpx_with_namespace(self):
        """Test parsing GPX file with XML namespace."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="50.0647" lon="19.9450"/>
      <trkpt lat="50.0650" lon="19.9455"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        wkt, suggested_date = parser.parse_gpx(gpx_content)

        assert wkt is not None
        assert wkt.startswith("LINESTRING")
        assert suggested_date is None

    def test_parse_gpx_invalid_xml(self):
        """Test parsing invalid XML raises InfrastructureException."""
        gpx_content = b"invalid xml content"

        parser = DjangoGpxParser()
        with pytest.raises(InfrastructureException, match="Nieprawidłowy plik lub podejrzana struktura XML"):
            parser.parse_gpx(gpx_content)

    def test_parse_gpx_no_track_points(self):
        """Test parsing GPX without track points raises InfrastructureException."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        with pytest.raises(InfrastructureException, match="Plik GPX nie zawiera ścieżki z punktami"):
            parser.parse_gpx(gpx_content)

    def test_parse_gpx_single_point(self):
        """Test parsing GPX with only one point raises InfrastructureException."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="50.0647" lon="19.9450"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        with pytest.raises(InfrastructureException, match="Ślad GPX jest za krótki"):
            parser.parse_gpx(gpx_content)

    def test_parse_gpx_invalid_coordinates(self):
        """Test parsing GPX with invalid coordinates skips invalid points."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="invalid" lon="19.9450"/>
      <trkpt lat="50.0650" lon="19.9455"/>
      <trkpt lat="50.0660" lon="invalid"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        # Should skip invalid points and parse the valid one
        # But since only one valid point remains, it should raise an exception
        with pytest.raises(InfrastructureException, match="Ślad GPX jest za krótki"):
            parser.parse_gpx(gpx_content)

    def test_parse_gpx_missing_lat_attribute(self):
        """Test parsing GPX with missing lat attribute."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lon="19.9450"/>
      <trkpt lat="50.0650" lon="19.9455"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        # Should skip the point with missing lat and parse the valid one
        # But since only one valid point remains, it should raise an exception
        with pytest.raises(InfrastructureException, match="Ślad GPX jest za krótki"):
            parser.parse_gpx(gpx_content)

    def test_parse_gpx_invalid_date_format(self):
        """Test parsing GPX with invalid date format returns None for date."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="50.0647" lon="19.9450">
        <time>invalid-date</time>
      </trkpt>
      <trkpt lat="50.0650" lon="19.9455"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        wkt, suggested_date = parser.parse_gpx(gpx_content)

        assert wkt is not None
        assert suggested_date is None

    def test_parse_gpx_no_time_element(self):
        """Test parsing GPX without time element returns None for date."""
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="50.0647" lon="19.9450"/>
      <trkpt lat="50.0650" lon="19.9455"/>
    </trkseg>
  </trk>
</gpx>"""

        parser = DjangoGpxParser()
        wkt, suggested_date = parser.parse_gpx(gpx_content)

        assert wkt is not None
        assert suggested_date is None
