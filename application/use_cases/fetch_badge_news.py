"""Use Case: Pobieranie nowości z portali turystycznych (US-A01)."""

from loguru import logger

from application.ports.news_port import NewsRepositoryPort, NewsScraperPort


class FetchBadgeNewsUseCase:
    """Pobiera nowości z portali turystycznych i zapisuje je do bazy."""

    def __init__(self, scraper: NewsScraperPort, repository: NewsRepositoryPort) -> None:
        """Inicjalizuje use case z scraperem i repozytorium."""
        self._scraper = scraper
        self._repo = repository

    def execute(self) -> str:
        """Pobiera newsy i zapisuje je do bazy omijając duplikaty.

        Zgodnie z US-A01: W razie błędu struktury HTML lub braku sieci,
        Use Case musi zignorować błąd (Fail-Silently), by nie wywalić nocnej kolejki Celery.
        """
        try:
            items = self._scraper.fetch_news()
        except Exception as e:
            logger.warning(f"Scraper odznak nie mógł pobrać danych (zignorowano błąd): {e}")
            return f"PRZERWANO (Ciche niepowodzenie): {e}"

        if not items:
            return "ZAKOŃCZONO: Nie znaleziono żadnych elementów na stronie."

        new_count = sum(1 for item in items if self._repo.save_news_item(item))

        return f"ZAKOŃCZONO: Pobrano {len(items)} elementów, z czego {new_count} to nowe wpisy."
