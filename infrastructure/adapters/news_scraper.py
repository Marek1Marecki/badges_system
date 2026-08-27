"""Adapter Scrapujący zewnętrzną witrynę przy użyciu BeautifulSoup."""

import logging
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

from application.dto.news_dto import BadgeNewsDTO
from application.ports.news_port import NewsScraperPort
from infrastructure.exceptions import InfrastructureException

logger = logging.getLogger(__name__)


class BeautifulSoupNewsScraper(NewsScraperPort):
    """Scraper newsów używający BeautifulSoup."""

    SOURCE_URL = "https://odznaki.org/zmiany/"

    def fetch_news(self) -> list[BadgeNewsDTO]:
        """Pobiera i parsuje newsy ze strony organizatora."""
        # Zabezpieczenie przed WAF: Udajemy przeglądarkę
        req = urllib.request.Request(self.SOURCE_URL, headers={"User-Agent": "BadgeSystem/1.0"})  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=15.0) as response:  # noqa: S310
                html_content = response.read().decode("utf-8")
        except Exception as e:
            raise InfrastructureException(f"Błąd sieci: {e}") from e

        # Używamy wbudowanego w Pythona parsera 'html.parser' (Zamiast 'lxml')
        soup = BeautifulSoup(html_content, "html.parser")

        # Szukamy nagłówka (bezpiecznie ignorując wielkość liter lub małe różnice spacji)
        header = soup.find(lambda tag: tag.name == "h2" and "Ostatnie 50 zmian" in tag.get_text())
        if not header:
            raise InfrastructureException("Nie znaleziono nagłówka sekcji zmian.")

        news_list = header.find_next_sibling("ul")
        if not news_list:
            raise InfrastructureException("Nie znaleziono listy ul z nowościami.")

        items = []
        for item in news_list.find_all("li"):
            icon_span = item.find("span", class_="material-icons")
            link_tag = item.find("a")
            if not icon_span or not link_tag:
                continue

            change_type_text = icon_span.get_text(strip=True)
            badge_name_str = link_tag.get_text(strip=True).replace(":", "")

            change_type = (
                "ADDITION"
                if "add_circle" in change_type_text
                else ("CHANGE" if "change_circle" in change_type_text else None)
            )

            # NOWE: Zabezpieczenie Observability (Ostrzeżenie o nieznanych ikonach)
            if change_type is None:
                logger.warning(
                    f"Nieznany typ ikony '{change_type_text}' na {self.SOURCE_URL} — "
                    "struktura strony mogła się zmienić lub dodano nowy typ zmian."
                )
                continue

            # Bezpieczne "rozpakowanie" atrybutu href dla lintera
            href_attr = link_tag.get("href")

            full_text = item.get_text(" ", strip=True)
            try:
                date_str = full_text.split("-")[0].strip()
            except IndexError:
                continue

            change_type = (
                "ADDITION"
                if "add_circle" in change_type_text
                else ("CHANGE" if "change_circle" in change_type_text else None)
            )

            href_attr = link_tag.get("href")
            if isinstance(href_attr, list):
                href_str = str(href_attr[0])
            elif isinstance(href_attr, str):
                href_str = href_attr
            else:
                href_str = ""

            if date_str and change_type and badge_name_str:
                items.append(
                    BadgeNewsDTO(
                        change_date_str=date_str,
                        change_type=change_type,
                        badge_name=badge_name_str,
                        source_url="https://odznaki.org" + href_str,
                    )
                )

        return items
