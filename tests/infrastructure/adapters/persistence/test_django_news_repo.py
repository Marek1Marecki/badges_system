"""Testy dla DjangoNewsRepository."""

from unittest.mock import MagicMock, patch

import pytest

from application.dto.news_dto import BadgeNewsDTO
from infrastructure.adapters.persistence.django_news_repo import DjangoNewsRepository


class TestDjangoNewsRepository:
    @patch("apps.badges.models.BadgeNewsItem")
    def test_save_news_item_creates_new_item(self, mock_model):
        """Tworzy nowy wpis news gdy nie istnieje."""
        repo = DjangoNewsRepository()
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="NEW",
            badge_name="Test Badge",
            source_url="https://example.com",
        )
        mock_model.objects.get_or_create.return_value = (MagicMock(), True)

        result = repo.save_news_item(dto)

        assert result is True
        mock_model.objects.get_or_create.assert_called_once_with(
            change_date_str="2023-01-01",
            change_type="NEW",
            badge_name="Test Badge",
            defaults={"source_url": "https://example.com"},
        )

    @patch("apps.badges.models.BadgeNewsItem")
    def test_save_news_item_returns_false_when_exists(self, mock_model):
        """Zwraca False gdy wpis już istnieje."""
        repo = DjangoNewsRepository()
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="NEW",
            badge_name="Test Badge",
            source_url="https://example.com",
        )
        mock_model.objects.get_or_create.return_value = (MagicMock(), False)

        result = repo.save_news_item(dto)

        assert result is False

    @patch("apps.badges.models.BadgeNewsItem")
    def test_save_news_item_deduplicates_by_composite_key(self, mock_model):
        """Deduplikuje na podstawie klucza złożonego."""
        repo = DjangoNewsRepository()
        dto = BadgeNewsDTO(
            change_date_str="2023-01-01",
            change_type="UPDATE",
            badge_name="Another Badge",
            source_url="https://example.com",
        )
        mock_model.objects.get_or_create.return_value = (MagicMock(), False)

        repo.save_news_item(dto)

        mock_model.objects.get_or_create.assert_called_once()
        call_kwargs = mock_model.objects.get_or_create.call_args[1]
        assert "change_date_str" in call_kwargs
        assert "change_type" in call_kwargs
        assert "badge_name" in call_kwargs
