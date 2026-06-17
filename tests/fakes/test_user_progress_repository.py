"""Testy jednostkowe dla FakeTouristRepository."""

from datetime import date

from application.dto.user_context_dto import TouristProfileDTO
from tests.fakes.user_progress_repository import FakeTouristRepository


class TestFakeTouristRepository:
    """Testuje wewnętrzną spójność pamięciowego repozytorium."""

    def test_tourist_profile_methods(self) -> None:
        repo = FakeTouristRepository()

        assert repo.get_profile(99) is None

        # Wstrzykujemy mocka profilu
        repo.profiles[99] = TouristProfileDTO(
            profile_id=99,
            is_main_profile=True,
            email="test@test",
            nickname="Test",
            active_plan="PRO",
            max_photos_per_ascent=5,
            max_active_badges=10,
        )

        profile = repo.get_profile(99)
        assert profile is not None
        assert profile.active_plan == "PRO"

    def test_ascent_log_methods(self) -> None:
        repo = FakeTouristRepository()

        assert repo.get_object_lifespan(15) == (None, None)
        assert repo.ascent_exists(profile_id=1, peak_id=15, ascent_date=date(2025, 1, 1)) is False
        assert repo.get_oldest_ascent_date(profile_id=1, badge_code="KGP") is None

        # Zapiszmy wejście
        ascent_id = repo.save_ascent(profile_id=1, peak_id=15, ascent_date=date(2025, 1, 1))
        assert ascent_id == 1
        assert repo.ascent_exists(profile_id=1, peak_id=15, ascent_date=date(2025, 1, 1)) is True
        assert repo.get_oldest_ascent_date(profile_id=1, badge_code="KGP") == date(2025, 1, 1)

        # Pobieranie niezużytych logów
        logs = repo.get_unconsumed_ascents(profile_id=1, badge_code="KGP", cutoff_date=None)
        assert len(logs) == 1

        # Odfiltrowanie przez cutoff date
        filtered_logs = repo.get_unconsumed_ascents(profile_id=1, badge_code="KGP", cutoff_date=date(2025, 12, 31))
        assert len(filtered_logs) == 0

    def test_user_progress_methods(self) -> None:
        repo = FakeTouristRepository()

        assert repo.get_active_progresses(profile_id=1) == []
        assert repo.get_progress(profile_id=1, badge_code="KGP", cycle_number=1) is None

        # Startujemy progres
        prog_id = repo.start_progress(profile_id=1, badge_code="KGP", version_id=42, cycle_number=1)
        assert prog_id == 1

        active = repo.get_active_progresses(profile_id=1)
        assert len(active) == 1
        assert active[0].domain_status == "NOT_STARTED"

        # Aktualizacja stanu domenowego
        repo.update_domain_status(prog_id, "COMPLETED")
        updated = repo.get_progress(profile_id=1, badge_code="KGP", cycle_number=1)
        assert updated is not None
        assert updated.domain_status == "COMPLETED"

        # Aktualizacja stanu logistycznego
        repo.update_logistic_status(prog_id, "WAITING_FOR_SEND", date(2025, 6, 1))
        logistics = repo.get_progress(profile_id=1, badge_code="KGP", cycle_number=1)
        assert logistics is not None
        assert logistics.logistic_status == "WAITING_FOR_SEND"
