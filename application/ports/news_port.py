"""Kontrakty dla Radaru Aktualności."""

from typing import Protocol

from application.dto.news_dto import BadgeNewsDTO


class NewsScraperPort(Protocol):
    """Port do scrapowania aktualności z portali turystycznych."""

    def fetch_news(self) -> list[BadgeNewsDTO]:
        """Pobiera listę aktualności odznak."""
        ...


class NewsRepositoryPort(Protocol):
    """Port do zapisywania aktualności w bazie danych."""

    def save_news_item(self, dto: BadgeNewsDTO) -> bool:
        """Zapisuje newsa.

        Zwraca True jeśli wpis jest nowy, False jeśli to duplikat.
                Args:
                  dto: BadgeNewsDTO:
                  dto: BadgeNewsDTO:

                Returns:
        """
        ...
