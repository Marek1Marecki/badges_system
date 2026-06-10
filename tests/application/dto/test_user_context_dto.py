"""Testy dla User Context DTOs."""

from datetime import date

from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO


class TestTouristProfileDTO:
    """Testy klasy TouristProfileDTO."""

    def test_tourist_profile_dto_creation_with_all_fields(self):
        """Test tworzenia TouristProfileDTO z wszystkimi polami."""
        dto = TouristProfileDTO(
            user_id=1,
            email="test@example.com",
            nickname="testuser",
            birth_date=date(2010, 1, 1),
            club_join_dates={"PTTK": date(2020, 1, 1)},
            active_plan="Pro",
            max_photos_per_ascent=5,
            max_active_badges=10,
        )

        assert dto.user_id == 1
        assert dto.email == "test@example.com"
        assert dto.nickname == "testuser"
        assert dto.birth_date == date(2010, 1, 1)
        assert dto.club_join_dates == {"PTTK": date(2020, 1, 1)}
        assert dto.active_plan == "Pro"
        assert dto.max_photos_per_ascent == 5
        assert dto.max_active_badges == 10

    def test_tourist_profile_dto_creation_with_minimal_fields(self):
        """Test tworzenia TouristProfileDTO z minimalnymi polami."""
        dto = TouristProfileDTO(
            user_id=1,
            email="test@example.com",
            nickname="testuser",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )

        assert dto.user_id == 1
        assert dto.birth_date is None
        assert dto.club_join_dates == {}

    def test_tourist_profile_dto_with_multiple_clubs(self):
        """Test TouristProfileDTO z wieloma klubami."""
        dto = TouristProfileDTO(
            user_id=1,
            email="test@example.com",
            nickname="testuser",
            club_join_dates={"PTTK": date(2020, 1, 1), "KGP": date(2021, 6, 1)},
            active_plan="Pro",
            max_photos_per_ascent=5,
            max_active_badges=10,
        )

        assert len(dto.club_join_dates) == 2

    def test_tourist_profile_dto_is_frozen(self):
        """Test że TouristProfileDTO jest immutable."""
        dto = TouristProfileDTO(
            user_id=1,
            email="test@example.com",
            nickname="testuser",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )

        # Pydantic frozen models prevent modification
        assert dto.model_config.get("frozen") is True


class TestBadgeProgressDTO:
    """Testy klasy BadgeProgressDTO."""

    def test_badge_progress_dto_creation_with_all_fields(self):
        """Test tworzenia BadgeProgressDTO z wszystkimi polami."""
        dto = BadgeProgressDTO(
            progress_id=1,
            user_id=1,
            badge_code="KGP",
            version_id=1,
            cycle_number=1,
            domain_status="IN_PROGRESS",
            logistic_status="WAITING_FOR_SEND",
            logistic_status_date=date(2026, 6, 1),
        )

        assert dto.progress_id == 1
        assert dto.user_id == 1
        assert dto.badge_code == "KGP"
        assert dto.version_id == 1
        assert dto.cycle_number == 1
        assert dto.domain_status == "IN_PROGRESS"
        assert dto.logistic_status == "WAITING_FOR_SEND"
        assert dto.logistic_status_date == date(2026, 6, 1)

    def test_badge_progress_dto_creation_with_minimal_fields(self):
        """Test tworzenia BadgeProgressDTO z minimalnymi polami."""
        dto = BadgeProgressDTO(
            progress_id=1,
            user_id=1,
            badge_code="KGP",
            version_id=1,
            cycle_number=1,
            domain_status="NOT_STARTED",
            logistic_status=None,
            logistic_status_date=None,
        )

        assert dto.progress_id == 1
        assert dto.logistic_status is None
        assert dto.logistic_status_date is None

    def test_badge_progress_dto_with_different_statuses(self):
        """Test BadgeProgressDTO z różnymi statusami."""
        dto = BadgeProgressDTO(
            progress_id=1,
            user_id=1,
            badge_code="KGP",
            version_id=1,
            cycle_number=1,
            domain_status="COMPLETED",
            logistic_status="ALBUM",
            logistic_status_date=date(2026, 6, 1),
        )

        assert dto.domain_status == "COMPLETED"
        assert dto.logistic_status == "ALBUM"

    def test_badge_progress_dto_is_frozen(self):
        """Test że BadgeProgressDTO jest immutable."""
        dto = BadgeProgressDTO(
            progress_id=1,
            user_id=1,
            badge_code="KGP",
            version_id=1,
            cycle_number=1,
            domain_status="NOT_STARTED",
            logistic_status=None,
            logistic_status_date=None,
        )

        # Pydantic frozen models prevent modification
        assert dto.model_config.get("frozen") is True
