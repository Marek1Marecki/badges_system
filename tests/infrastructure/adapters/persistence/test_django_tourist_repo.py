"""Testy integracyjne dla DjangoTouristRepository — bez mocków ORM."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from application.dto.ascent_dto import AscentRequestDTO
from application.dto.user_context_dto import TouristProfileDTO
from infrastructure.adapters.persistence.django_tourist_repo import DjangoTouristRepository

User = get_user_model()


def _create_user(username: str, email: str) -> User:
    user = User.objects.create_user(username=username, email=email)
    user.set_password("pass")
    user.save()
    return user


def _create_organizer():
    from apps.badges.models import OrganizerModel

    return OrganizerModel.objects.create(name="PTTK")


@pytest.mark.integration
@pytest.mark.django_db
class TestDjangoTouristRepository:
    """Testy oparte na prawdziwej bazie danych PostgreSQL."""

    def setup_method(self):
        self.repo = DjangoTouristRepository()

    def test_get_profile_returns_dto(self):
        """Zwraca TouristProfileDTO dla istniejącego profilu."""
        user = _create_user("turysta", "turysta@example.com")
        profile = user.profiles.create(
            nickname="Turysta",
            birth_date=date(1990, 1, 1),
            active_plan="FREE",
        )

        result = self.repo.get_profile(profile.id)

        assert isinstance(result, TouristProfileDTO)
        assert result.profile_id == profile.id
        assert result.nickname == "Turysta"
        assert result.email == "turysta@example.com"

    def test_get_profile_returns_none_when_missing(self):
        """Zwraca None gdy profil nie istnieje."""
        result = self.repo.get_profile(99999)
        assert result is None

    def test_get_object_lifespan(self):
        """Zwraca ramy życia obiektu turystycznego."""
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(
            name="Test Peak",
            type="Szczyt",
            existence_start=date(2000, 1, 1),
            existence_end=date(2099, 12, 31),
            is_active=True,
            status="READY",
        )

        start, end = self.repo.get_object_lifespan(obj.id)

        assert start == date(2000, 1, 1)
        assert end == date(2099, 12, 31)

    def test_get_object_lifespan_returns_none_when_missing(self):
        """Zwraca None gdy obiekt nie istnieje."""
        result = self.repo.get_object_lifespan(99999)
        assert result is None

    def test_ascent_exists(self):
        """Zwraca True gdy wejście istnieje."""
        user = _create_user("turysta2", "t2@example.com")
        profile = user.profiles.create(nickname="T2", birth_date=date(1990, 1, 1))
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(name="Peak", type="Szczyt", is_active=True, status="READY")

        self.repo.save_ascent(profile.id, obj.id, date(2023, 1, 1))

        assert self.repo.ascent_exists(profile.id, obj.id, date(2023, 1, 1)) is True
        assert self.repo.ascent_exists(profile.id, obj.id, date(2023, 1, 2)) is False

    def test_save_ascent_idempotent(self):
        """Upsert jest idempotentny — drugie wywołanie nie rzuca błędu."""
        user = _create_user("turysta3", "t3@example.com")
        profile = user.profiles.create(nickname="T3", birth_date=date(1990, 1, 1))
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(name="Peak3", type="Szczyt", is_active=True, status="READY")

        id1 = self.repo.save_ascent(profile.id, obj.id, date(2023, 6, 1))
        id2 = self.repo.save_ascent(profile.id, obj.id, date(2023, 6, 1))

        assert id1 == id2

    def test_get_oldest_ascent_date(self):
        """Zwraca najstarszą datę wejścia na szczyt z puli odznaki."""
        user = _create_user("turysta4", "t4@example.com")
        profile = user.profiles.create(nickname="T4", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel, TouristObject

        badge = BadgeModel.objects.create(code="KGP", name="Korona Gór Polski", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        obj = TouristObject.objects.create(name="P1", type="Szczyt", is_active=True, status="READY")
        version.pool_peaks.add(obj)

        self.repo.save_ascent(profile.id, obj.id, date(2023, 1, 1))
        self.repo.save_ascent(profile.id, obj.id, date(2023, 6, 1))

        oldest = self.repo.get_oldest_ascent_date(profile.id, "KGP")

        assert oldest == date(2023, 1, 1)

    def test_bulk_save_ascents_ignores_duplicates(self):
        """ignore_conflicts=True chroni przed duplikatami UniqueConstraint."""
        user = _create_user("turysta5", "t5@example.com")
        profile = user.profiles.create(nickname="T5", birth_date=date(1990, 1, 1))
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(name="P5", type="Szczyt", is_active=True, status="READY")

        dtos = [AscentRequestDTO(peak_id=obj.id, ascent_date=date(2023, 1, 1)) for _ in range(3)]
        self.repo.bulk_save_ascents(profile.id, dtos)

        from apps.tourists.models import AscentLog

        count_after_first = AscentLog.objects.filter(profile=profile, peak=obj, ascent_date=date(2023, 1, 1)).count()
        assert count_after_first == 1

        self.repo.bulk_save_ascents(profile.id, dtos)

        count_after_second = AscentLog.objects.filter(profile=profile, peak=obj, ascent_date=date(2023, 1, 1)).count()
        assert count_after_second == 1

    def test_start_progress_creates_progress(self):
        """Tworzy nowy postęp odznaki."""
        user = _create_user("turysta6", "t6@example.com")
        profile = user.profiles.create(nickname="T6", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP", name="Korona Gór Polski", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))

        progress_id = self.repo.start_progress(profile.id, "KGP", version.id)

        assert progress_id is not None
        progress = self.repo.get_progress(profile.id, "KGP", 1)
        assert progress is not None
        assert progress.badge_code == "KGP"
        assert progress.domain_status == "NOT_STARTED"

    def test_update_domain_status(self):
        """Aktualizuje status domenowy postępu."""
        user = _create_user("turysta7", "t7@example.com")
        profile = user.profiles.create(nickname="T7", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP2", name="Test", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        progress_id = self.repo.start_progress(profile.id, "KGP2", version.id)

        self.repo.update_domain_status(progress_id, "IN_PROGRESS")

        progress = self.repo.get_progress(profile.id, "KGP2", 1)
        assert progress.domain_status == "IN_PROGRESS"

    def test_update_logistic_status(self):
        """Aktualizuje status logistyczny postępu."""
        user = _create_user("turysta8", "t8@example.com")
        profile = user.profiles.create(nickname="T8", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP3", name="Test3", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        progress_id = self.repo.start_progress(profile.id, "KGP3", version.id)

        self.repo.update_logistic_status(progress_id, "WAITING_FOR_SEND", date(2024, 6, 1))

        progress = self.repo.get_progress(profile.id, "KGP3", 1)
        assert progress.logistic_status == "WAITING_FOR_SEND"
        assert progress.logistic_status_date == date(2024, 6, 1)

    def test_get_completed_badge_codes(self):
        """Zwraca kody ukończonych odznak."""
        user = _create_user("turysta9", "t9@example.com")
        profile = user.profiles.create(nickname="T9", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP4", name="Test4", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        self.repo.start_progress(profile.id, "KGP4", version.id)
        self.repo.update_domain_status(self.repo.get_progress(profile.id, "KGP4", 1).progress_id, "COMPLETED")

        codes = self.repo.get_completed_badge_codes(profile.id)

        assert "KGP4" in codes

    def test_get_progress_by_id(self):
        """Zwraca postęp po ID."""
        user = _create_user("turysta10", "t10@example.com")
        profile = user.profiles.create(nickname="T10", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP5", name="Test5", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        progress_id = self.repo.start_progress(profile.id, "KGP5", version.id)

        progress = self.repo.get_progress_by_id(profile.id, progress_id)

        assert progress is not None
        assert progress.badge_code == "KGP5"

    def test_get_progress_by_id_returns_none_for_other_profile(self):
        """Zwraca None gdy postęp należy do innego profilu."""
        user1 = _create_user("u1", "u1@example.com")
        user2 = _create_user("u2", "u2@example.com")
        profile1 = user1.profiles.create(nickname="P1", birth_date=date(1990, 1, 1))
        profile2 = user2.profiles.create(nickname="P2", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP6", name="Test6", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        progress_id = self.repo.start_progress(profile1.id, "KGP6", version.id)

        result = self.repo.get_progress_by_id(profile2.id, progress_id)

        assert result is None

    def test_get_all_unarchived_progresses(self):
        """Zwraca listę aktywnych postępów profilu."""
        user = _create_user("turysta11", "t11@example.com")
        profile = user.profiles.create(nickname="T11", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP7", name="Test7", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        self.repo.start_progress(profile.id, "KGP7", version.id)

        progresses = self.repo.get_all_unarchived_progresses(profile.id)

        assert len(progresses) == 1
        assert progresses[0].badge_code == "KGP7"

    def test_delete_progress(self):
        """Usuwa postęp odznaki."""
        user = _create_user("turysta12", "t12@example.com")
        profile = user.profiles.create(nickname="T12", birth_date=date(1990, 1, 1))
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP8", name="Test8", organizer=_create_organizer())
        BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))

        self.repo.delete_progress(profile.id, "KGP8")

        assert self.repo.get_progress(profile.id, "KGP8", 1) is None

    def test_get_all_ascents_for_user(self):
        """Zwraca wszystkie wejścia użytkownika z regionami CQRS."""
        user = _create_user("turysta13", "t13@example.com")
        profile = user.profiles.create(nickname="T13", birth_date=date(1990, 1, 1))
        from apps.badges.models import ObjectRegionCache, TouristObject

        obj = TouristObject.objects.create(name="P13", type="Szczyt", is_active=True, status="READY")
        ObjectRegionCache.objects.create(
            tourist_object=obj,
            region_level="voivodeship",
            region_id=1,
            region_name="Test Region",
            distance_meters=0.0,
        )

        self.repo.save_ascent(profile.id, obj.id, date(2023, 1, 1))

        ascents = self.repo.get_all_ascents_for_user(profile.id)

        assert len(ascents) == 1
        assert ascents[0].object_id == obj.id
        assert ascents[0].region_ids == frozenset({1})
