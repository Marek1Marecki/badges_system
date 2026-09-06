"""Kontrakty dla Radaru Aktualności."""

from typing import Protocol

from application.dto.news_dto import BadgeNewsResponseDTO


class NewsScraperPort(Protocol):
    """Port do scrapowania aktualności z portali turystycznych."""

    def fetch_news(self) -> list[BadgeNewsResponseDTO]:
        """Pobiera listę aktualności odznak."""
        ...


class NewsRepositoryPort(Protocol):
    """Port do zapisywania aktualności w bazie danych."""

    def save_news_item(self, dto: BadgeNewsResponseDTO) -> bool:
        """Zapisuje newsa.

        Zwraca True jeśli wpis jest nowy, False jeśli to duplikat.
        """
        ...
