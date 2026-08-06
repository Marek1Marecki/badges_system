"""Testy integracyjne dla komendy restore_reference_data — weryfikacja idempotentności."""

from pathlib import Path

import pytest
from django.core.management import call_command

from apps.badges.models import BadgeNewsItem


@pytest.mark.integration
@pytest.mark.django_db
class TestRestoreReferenceDataIdempotency:
    """Weryfikuje, że restore_reference_data nie nadpisuje danych przy powtórnym uruchomieniu."""

    def test_loaddata_is_idempotent(self, settings):
        """loaddata nie duplikuje rekordów przy powtórnym ładowaniu tego samego fixture'a."""
        data_dir = Path(settings.BASE_DIR) / "data" / "reference"
        if not data_dir.exists():
            pytest.skip("Brak katalogu data/reference z fixture'ami")

        fixture_file = data_dir / "05_badge_news.json.gz"
        if not fixture_file.exists():
            pytest.skip("Brak fixture'a 05_badge_news.json.gz")

        call_command("loaddata", str(fixture_file))
        count_after_first = BadgeNewsItem.objects.count()

        call_command("loaddata", str(fixture_file))

        count_after_second = BadgeNewsItem.objects.count()
        assert count_after_second == count_after_first
