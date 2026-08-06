"""Testy integracyjne dla DjangoNewsRepository — bez mocków ORM."""

import pytest

from application.dto.news_dto import BadgeNewsDTO
from infrastructure.adapters.persistence.django_news_repo import DjangoNewsRepository


@pytest.mark.integration
@pytest.mark.django_db
class TestDjangoNewsRepository:
    """Testy oparte na prawdziwej bazie danych PostgreSQL."""

    def setup_method(self):
        self.repo = DjangoNewsRepository()

    def test_save_news_item_creates_new_item(self):
        """Tworzy nowy wpis news gdy nie istnieje."""
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="NEW",
            badge_name="Test Badge",
            source_url="https://example.com",
        )

        result = self.repo.save_news_item(dto)

        assert result is True
        assert self.repo.__class__.__name__ == "DjangoNewsRepository"

    def test_save_news_item_returns_false_when_exists(self):
        """Zwraca False gdy wpis już istnieje (idempotentność)."""
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="NEW",
            badge_name="Test Badge",
            source_url="https://example.com",
        )

        self.repo.save_news_item(dto)
        result = self.repo.save_news_item(dto)

        assert result is False

    def test_save_news_item_deduplicates_by_composite_key(self):
        """Deduplikuje na podstawie klucza złożonego."""
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="UPDATE",
            badge_name="Another Badge",
            source_url="https://example.com",
        )

        self.repo.save_news_item(dto)
        self.repo.save_news_item(dto)

        from apps.badges.models import BadgeNewsItem

        count = BadgeNewsItem.objects.filter(
            change_date_str="2023-01-01",
            change_type="UPDATE",
            badge_name="Another Badge",
        ).count()
        assert count == 1
