"""Testy dla wartości domenowych."""

from datetime import date

import pytest

from domain.value_objects.ascent import ActivityType, Ascent


class TestActivityType:
    """Testy klasy ActivityType."""

    def test_activity_type_values(self):
        """Test wartości enuma ActivityType."""
        assert ActivityType.HIKING.value == "HIKING"
        assert ActivityType.CYCLING.value == "CYCLING"
        assert ActivityType.SKIING.value == "SKIING"

    def test_activity_type_is_enum(self):
        """Test że ActivityType jest enumem."""
        assert hasattr(ActivityType, "__members__")
        assert len(ActivityType) == 3
        assert "HIKING" in ActivityType.__members__
        assert "CYCLING" in ActivityType.__members__
        assert "SKIING" in ActivityType.__members__


class TestAscent:
    """Testy klasy Ascent."""

    def test_ascent_creation(self):
        """Test tworzenia obiektu Ascent."""
        ascent_date = date(2023, 1, 1)
        ascent = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)

        assert ascent.peak_id == 1
        assert ascent.ascent_date == ascent_date
        assert ascent.activity == ActivityType.HIKING

    def test_ascent_with_different_activity_types(self):
        """Test tworzenia obiektu Ascent z różnymi typami aktywności."""
        ascent_date = date(2023, 6, 1)

        hiking_ascent = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)
        cycling_ascent = Ascent(peak_id=2, ascent_date=ascent_date, activity=ActivityType.CYCLING)
        skiing_ascent = Ascent(peak_id=3, ascent_date=ascent_date, activity=ActivityType.SKIING)

        assert hiking_ascent.activity == ActivityType.HIKING
        assert cycling_ascent.activity == ActivityType.CYCLING
        assert skiing_ascent.activity == ActivityType.SKIING

    def test_ascent_with_different_dates(self):
        """Test tworzenia obiektu Ascent z różnymi datami."""
        dates = [
            date(2020, 1, 1),
            date(2023, 6, 15),
            date(2024, 12, 31),
        ]

        for i, test_date in enumerate(dates):
            ascent = Ascent(peak_id=i + 1, ascent_date=test_date, activity=ActivityType.HIKING)
            assert ascent.ascent_date == test_date

    def test_ascent_with_different_peak_ids(self):
        """Test tworzenia obiektu Ascent z różnymi ID szczytów."""
        peak_ids = [1, 42, 999, 0, -1]
        test_date = date(2023, 1, 1)

        for peak_id in peak_ids:
            ascent = Ascent(peak_id=peak_id, ascent_date=test_date, activity=ActivityType.HIKING)
            assert ascent.peak_id == peak_id

    def test_ascent_is_frozen(self):
        """Test że Ascent jest immutable (frozen)."""
        ascent = Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING)

        with pytest.raises(AttributeError):
            ascent.peak_id = 2

        with pytest.raises(AttributeError):
            ascent.ascent_date = date(2023, 2, 1)

        with pytest.raises(AttributeError):
            ascent.activity = ActivityType.CYCLING

    def test_ascent_equality(self):
        """Test równości obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)
        ascent2 = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)
        ascent3 = Ascent(peak_id=2, ascent_date=ascent_date, activity=ActivityType.HIKING)

        assert ascent1 == ascent2
        assert ascent1 != ascent3

    def test_ascent_hash(self):
        """Test haszowania obiektów Ascent."""
        ascent_date = date(2023, 1, 1)

        ascent1 = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)
        ascent2 = Ascent(peak_id=1, ascent_date=ascent_date, activity=ActivityType.HIKING)

        assert hash(ascent1) == hash(ascent2)

        # Test that Ascent can be used in a set
        ascent_set = {ascent1, ascent2}
        assert len(ascent_set) == 1

    def test_ascent_repr(self):
        """Test reprezentacji tekstowej obiektu Ascent."""
        ascent = Ascent(peak_id=1, ascent_date=date(2023, 1, 1), activity=ActivityType.HIKING)

        repr_str = repr(ascent)
        assert "Ascent" in repr_str
        assert "peak_id=1" in repr_str
        assert "ActivityType.HIKING" in repr_str

    def test_ascent_with_edge_case_dates(self):
        """Test Ascent z datami granicznymi."""
        # Test with very old date
        old_ascent = Ascent(peak_id=1, ascent_date=date(1900, 1, 1), activity=ActivityType.HIKING)
        assert old_ascent.ascent_date == date(1900, 1, 1)

        # Test with future date
        future_ascent = Ascent(peak_id=2, ascent_date=date(2100, 12, 31), activity=ActivityType.CYCLING)
        assert future_ascent.ascent_date == date(2100, 12, 31)
