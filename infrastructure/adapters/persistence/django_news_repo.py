"""Adapter zapisu newsów do PostGIS."""

from application.dto.news_dto import BadgeNewsResponseDTO
from application.ports.news_port import NewsRepositoryPort


class DjangoNewsRepository(NewsRepositoryPort):
    """Repozytorium newsów oparte o Django ORM."""

    def save_news_item(self, dto: BadgeNewsResponseDTO) -> bool:
        """

        Args:
          dto: BadgeNewsResponseDTO:
          dto: BadgeNewsResponseDTO:

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
