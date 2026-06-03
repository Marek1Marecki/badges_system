"""Testy dla wartości domenowych."""

from datetime import date

from domain.value_objects.ascent import Ascent


class TestAscent:
    """Testy klasy Ascent."""

    def test_ascent_creation(self):
        """Test tworzenia obiektu Ascent."""
        ascent_date = date(2023, 1, 1)
        ascent = Ascent(peak_id=1, ascent_date=ascent_date)

        assert ascent.peak_id == 1
        assert ascent.ascent_date == ascent_date

    def test_ascent_with_different_dates(self):
        """Test tworzenia obiektu Ascent z różnymi datami."""
        dates = [
            date(2020, 1, 1),
            date(2023, 6, 15),
            date(2024, 12, 31),
        ]

        for i, test_date in enumerate(dates):
            ascent = Ascent(peak_id=i + 1, ascent_date=test_date)
            assert ascent.ascent_date == test_date

    def test_ascent_with_different_peak_ids(self):
        """Test tworzenia obiektu Ascent z różnymi ID szczytów."""
        peak_ids = [1, 42, 999, 0, -1]
        test_date = date(2023, 1, 1)

        for peak_id in peak_ids:
            ascent = Ascent(peak_id=peak_id, ascent_date=test_date)
            assert ascent.peak_id == peak_id

    def test_ascent_equality(self):
        """Test równości obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(peak_id=1, ascent_date=ascent_date)
        ascent2 = Ascent(peak_id=1, ascent_date=ascent_date)
        ascent3 = Ascent(peak_id=2, ascent_date=ascent_date)

        assert ascent1 == ascent2
        assert ascent1 != ascent3

    def test_ascent_hash(self):
        """Test haszowania obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(peak_id=1, ascent_date=ascent_date)
        ascent2 = Ascent(peak_id=1, ascent_date=ascent_date)

        assert hash(ascent1) == hash(ascent2)

        # Test that Ascent can be used in a set
        ascent_set = {ascent1, ascent2}
        assert len(ascent_set) == 1

    def test_ascent_repr(self):
        """Test reprezentacji tekstowej obiektu Ascent."""
        ascent = Ascent(peak_id=1, ascent_date=date(2023, 1, 1))

        repr_str = repr(ascent)
        assert "Ascent" in repr_str
        assert "peak_id=1" in repr_str

    def test_ascent_with_edge_case_dates(self):
        """Test Ascent z datami granicznymi."""
        # Test with very old date
        old_ascent = Ascent(peak_id=1, ascent_date=date(1900, 1, 1))
        assert old_ascent.ascent_date == date(1900, 1, 1)

        # Test with future date
        future_ascent = Ascent(peak_id=2, ascent_date=date(2100, 12, 31))
        assert future_ascent.ascent_date == date(2100, 12, 31)
