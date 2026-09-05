"""Testy dla wartości domenowych."""

from datetime import date

from domain.value_objects.ascent import Ascent


class TestAscent:
    """Testy klasy Ascent."""

    def test_ascent_creation(self):
        """Test tworzenia obiektu Ascent."""
        ascent_date = date(2023, 1, 1)
        ascent = Ascent(object_id=1, ascent_date=ascent_date)

        assert ascent.object_id == 1
        assert ascent.ascent_date == ascent_date

    def test_ascent_with_different_dates(self):
        """Test tworzenia obiektu Ascent z różnymi datami."""
        dates = [
            date(2020, 1, 1),
            date(2023, 6, 15),
            date(2024, 12, 31),
        ]

        for i, test_date in enumerate(dates):
            ascent = Ascent(object_id=i + 1, ascent_date=test_date)
            assert ascent.ascent_date == test_date

    def test_ascent_with_different_object_ids(self):
        """Test tworzenia obiektu Ascent z różnymi ID obiektów turystycznych."""
        object_ids = [1, 42, 999, 0, -1]
        test_date = date(2023, 1, 1)

        for object_id in object_ids:
            ascent = Ascent(object_id=object_id, ascent_date=test_date)
            assert ascent.object_id == object_id

    def test_ascent_equality(self):
        """Test równości obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(object_id=1, ascent_date=ascent_date)
        ascent2 = Ascent(object_id=1, ascent_date=ascent_date)
        ascent3 = Ascent(object_id=2, ascent_date=ascent_date)

        assert ascent1 == ascent2
        assert ascent1 != ascent3

    def test_ascent_hash(self):
        """Test haszowania obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(object_id=1, ascent_date=ascent_date)
        ascent2 = Ascent(object_id=1, ascent_date=ascent_date)

        assert hash(ascent1) == hash(ascent2)

        # Test that Ascent can be used in a set
        ascent_set = {ascent1, ascent2}
        assert len(ascent_set) == 1

    def test_ascent_repr(self):
        """Test reprezentacji tekstowej obiektu Ascent."""
        ascent = Ascent(object_id=1, ascent_date=date(2023, 1, 1))

        repr_str = repr(ascent)
        assert "Ascent" in repr_str
        assert "object_id=1" in repr_str

    def test_ascent_with_edge_case_dates(self):
        """Test Ascent z datami granicznymi."""
        # Test with very old date
        old_ascent = Ascent(object_id=1, ascent_date=date(1900, 1, 1))
        assert old_ascent.ascent_date == date(1900, 1, 1)

        # Test with future date
        future_ascent = Ascent(object_id=2, ascent_date=date(2100, 12, 31))
        assert future_ascent.ascent_date == date(2100, 12, 31)
