"""Tests for BulkLogAscentsUseCase."""

from datetime import UTC, date, datetime

from application.dto.ascent_dto import AscentRequestDTO, BulkAscentResultDTO
from application.services.bitemporal_validation_service import BitemporalValidationService
from application.use_cases.bulk_log_ascents import BulkLogAscentsUseCase
from tests.fakes.clock import FakeClock
from tests.fakes.mocks import MockEventPublisher, MockUnitOfWork

MOCK_CLOCK_TIME = datetime(2023, 6, 15, tzinfo=UTC)


class MockAscentRepository:
    def get_objects_lifespans(self, peak_ids):
        return {
            1: (date(2020, 1, 1), None),
            2: (date(2021, 1, 1), date(2022, 1, 1)),
        }

    def bulk_save_ascents(self, profile_id, ascents):
        return len(ascents)


def _clock() -> FakeClock:
    """Deterministic clock matching the original MockClock semantics."""
    return FakeClock(fixed_time=MOCK_CLOCK_TIME)


def _use_case(repo: MockAscentRepository, clock: FakeClock) -> BulkLogAscentsUseCase:
    """Buduje BulkLogAscentsUseCase z realnym BitemporalValidationService (AUDYT-017)."""
    return BulkLogAscentsUseCase(
        repo,
        BitemporalValidationService(repo, clock),
        MockUnitOfWork(),
        MockEventPublisher(),
    )


class TestBulkLogAscentsUseCase:
    """Test BulkLogAscentsUseCase."""

    def test_execute_with_empty_list(self):
        """Test execute with empty ascents list."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        result = use_case.execute(1, [])

        assert result.saved_count == 0
        assert result.errors == []

    def test_execute_with_valid_ascents(self):
        """Test execute with valid ascents."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [
            AscentRequestDTO(peak_id=1, ascent_date=date(2023, 1, 1)),
            AscentRequestDTO(peak_id=1, ascent_date=date(2023, 2, 1)),
        ]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 2
        assert result.errors == []

    def test_execute_with_future_date(self):
        """Test execute rejects ascents with future dates."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [AscentRequestDTO(peak_id=1, ascent_date=date(2024, 1, 1))]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 0
        assert len(result.errors) == 1
        assert "z przyszłości" in result.errors[0]["reason"]

    def test_execute_with_nonexistent_object(self):
        """Test execute rejects ascents for nonexistent objects."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [AscentRequestDTO(peak_id=999, ascent_date=date(2023, 1, 1))]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 0
        assert len(result.errors) == 1
        assert "nie istnieje" in result.errors[0]["reason"]

    def test_execute_with_date_before_object_creation(self):
        """Test execute rejects ascents before object creation."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [AscentRequestDTO(peak_id=1, ascent_date=date(2019, 1, 1))]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 0
        assert len(result.errors) == 1
        assert "nie istniał" in result.errors[0]["reason"]

    def test_execute_with_date_after_object_destruction(self):
        """Test execute rejects ascents after object destruction."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [AscentRequestDTO(peak_id=2, ascent_date=date(2023, 1, 1))]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 0
        assert len(result.errors) == 1
        assert "zniszczono" in result.errors[0]["reason"] or "wyłączony" in result.errors[0]["reason"]

    def test_execute_with_mixed_valid_and_invalid(self):
        """Test execute with mixed valid and invalid ascents."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [
            AscentRequestDTO(peak_id=1, ascent_date=date(2023, 1, 1)),  # Valid
            AscentRequestDTO(peak_id=999, ascent_date=date(2023, 1, 1)),  # Nonexistent
            AscentRequestDTO(peak_id=1, ascent_date=date(2024, 1, 1)),  # Future
        ]

        result = use_case.execute(1, ascents)

        assert result.saved_count == 1
        assert len(result.errors) == 2

    def test_execute_returns_bulk_ascent_result_dto(self):
        """Test execute returns BulkAscentResultDTO."""
        repo = MockAscentRepository()
        clock = _clock()
        use_case = _use_case(repo, clock)

        ascents = [AscentRequestDTO(peak_id=1, ascent_date=date(2023, 1, 1))]

        result = use_case.execute(1, ascents)

        assert isinstance(result, BulkAscentResultDTO)
        assert result.saved_count == 1
        assert hasattr(result, "errors")
