"""Adapter zapisu newsów do PostGIS."""

from application.dto.news_dto import BadgeNewsDTO
from application.ports.news_port import NewsRepositoryPort


class DjangoNewsRepository(NewsRepositoryPort):
    """"""

    def save_news_item(self, dto: BadgeNewsDTO) -> bool:
        """

        Args:
          dto: BadgeNewsDTO:
          dto: BadgeNewsDTO:

        Returns:

        """
        from apps.badges.models import BadgeNewsItem

        # get_or_create to idealny Upsert z deduplikacją!
        _, created = BadgeNewsItem.objects.get_or_create(
            change_date_str=dto.change_date_str,
            change_type=dto.change_type,
            badge_name=dto.badge_name,
            defaults={"source_url": dto.source_url},
        )
        return bool(created)
