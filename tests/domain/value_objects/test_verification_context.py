"""Testy dla VerificationContext."""

from datetime import UTC, date, datetime

from domain.value_objects.verification_context import VerificationContext


class TestVerificationContext:
    """Testy klasy VerificationContext."""

    def test_verification_context_creation_with_all_fields(self):
        """Test tworzenia VerificationContext z wszystkimi polami."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            tourist_birth_date=date(2010, 1, 1),
            club_join_dates={"PTTK": date(2020, 1, 1)},
            completed_badge_codes=frozenset(["KGP"]),
        )

        assert ctx.evaluation_time == datetime(2026, 6, 1, tzinfo=UTC)
        assert ctx.tourist_birth_date == date(2010, 1, 1)
        assert ctx.club_join_dates == {"PTTK": date(2020, 1, 1)}
        assert ctx.completed_badge_codes == frozenset(["KGP"])

    def test_verification_context_creation_with_minimal_fields(self):
        """Test tworzenia VerificationContext z minimalnymi polami."""
        ctx = VerificationContext(evaluation_time=datetime(2026, 6, 1, tzinfo=UTC))

        assert ctx.evaluation_time == datetime(2026, 6, 1, tzinfo=UTC)
        assert ctx.tourist_birth_date is None
        assert ctx.club_join_dates == {}
        assert ctx.completed_badge_codes == frozenset()

    def test_verification_context_with_empty_club_dates(self):
        """Test VerificationContext z pustym słownikiem klubów."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            club_join_dates={},
        )

        assert ctx.club_join_dates == {}

    def test_verification_context_with_multiple_club_dates(self):
        """Test VerificationContext z wieloma datami dołączenia do klubów."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            club_join_dates={"PTTK": date(2020, 1, 1), "KGP": date(2021, 6, 1)},
        )

        assert len(ctx.club_join_dates) == 2
        assert ctx.club_join_dates["PTTK"] == date(2020, 1, 1)
        assert ctx.club_join_dates["KGP"] == date(2021, 6, 1)

    def test_verification_context_with_multiple_completed_badges(self):
        """Test VerificationContext z wieloma ukończonymi odznakami."""
        ctx = VerificationContext(
            evaluation_time=datetime(2026, 6, 1, tzinfo=UTC),
            completed_badge_codes=frozenset(["KGP", "KSP", "KORONA"]),
        )

        assert len(ctx.completed_badge_codes) == 3
        assert "KGP" in ctx.completed_badge_codes
        assert "KSP" in ctx.completed_badge_codes
        assert "KORONA" in ctx.completed_badge_codes

    def test_verification_context_is_frozen(self):
        """Test że VerificationContext jest immutable."""
        ctx = VerificationContext(evaluation_time=datetime(2026, 6, 1, tzinfo=UTC))

        try:
            ctx.evaluation_time = datetime(2026, 7, 1, tzinfo=UTC)
            assert False, "Should not be able to modify frozen dataclass"
        except (AttributeError, TypeError):
            pass  # Expected for frozen dataclass
