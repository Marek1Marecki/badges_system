"""Testy walidacji temporalnej BadgeVersionModel (AUDYT-099)."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.badges.models import BadgeModel, BadgeVersionModel, OrganizerModel


@pytest.fixture
def organizer():
    return OrganizerModel.objects.create(name="PTTK")


@pytest.fixture
def badge(organizer):
    return BadgeModel.objects.create(code="KGP", name="KGP", organizer=organizer)


@pytest.mark.django_db(transaction=True)
class TestBadgeVersionModelTemporalClean:
    """End-Date Policy — Temporal Collision Detection."""

    def test_clean_allows_open_version_with_no_siblings(self, badge):
        """Pierwsza wersja odznki może mieć valid_to=None."""
        version = BadgeVersionModel(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1), valid_to=None)
        version.clean()

    def test_clean_raises_when_open_past_version_exists(self, badge):
        """Blokada: nie można dodać nowej wersji gdy stara jest otwarta w przeszłości."""
        BadgeVersionModel.objects.create(badge=badge, version_code="v_old", valid_from=date(2020, 1, 1), valid_to=None)
        new_version = BadgeVersionModel(badge=badge, version_code="v_new", valid_from=date(2026, 1, 1), valid_to=None)

        with pytest.raises(ValidationError, match="Zakończ najpierw"):
            new_version.clean()

    def test_clean_allows_overlap_when_old_version_has_valid_to(self, badge):
        """Okres pokrywania się (Grace Period) jest dozwolony gdy stara wersja ma valid_to."""
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v_old",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
        )
        new_version = BadgeVersionModel(
            badge=badge,
            version_code="v_new",
            valid_from=date(2026, 5, 1),
            valid_to=None,
        )
        new_version.clean()

    def test_clean_allows_new_version_when_existing_is_expired(self, badge):
        """Można dodać nową wersję gdy istniejąca jest już wygasła (valid_to < today)."""
        BadgeVersionModel.objects.create(
            badge=badge, version_code="v_old", valid_from=date(2020, 1, 1), valid_to=date(2022, 1, 1)
        )
        new_version = BadgeVersionModel(badge=badge, version_code="v_new", valid_from=date(2024, 1, 1), valid_to=None)
        new_version.clean()

    def test_clean_allows_draft_future_version_when_old_version_has_valid_to(self, badge):
        """DRAFT w przyszłości jest dozwolony gdy poprzednia wersja ma ustawione valid_to."""
        BadgeVersionModel.objects.create(
            badge=badge, version_code="v_current", valid_from=date(2024, 1, 1), valid_to=date(2025, 12, 31)
        )
        draft = BadgeVersionModel(
            badge=badge, version_code="v_draft_future", valid_from=date(2099, 1, 1), valid_to=None
        )
        draft.clean()

    def test_clean_blocks_draft_future_when_open_past_exists(self, badge):
        """DRAFT w przyszłości jest blokowany gdy istnieje otwarta wersja w przeszłości."""
        BadgeVersionModel.objects.create(
            badge=badge, version_code="v_current", valid_from=date(2024, 1, 1), valid_to=None
        )
        draft = BadgeVersionModel(
            badge=badge, version_code="v_draft_future", valid_from=date(2099, 1, 1), valid_to=None
        )

        with pytest.raises(ValidationError, match="Zakończ najpierw"):
            draft.clean()
