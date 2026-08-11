"""Tests for BeautifulSoupNewsScraper."""

import pytest

from infrastructure.adapters.news_scraper import BeautifulSoupNewsScraper
from infrastructure.exceptions import InfrastructureException


class MockResponse:
    def __init__(self, html_content):
        self.html_content = html_content

    def read(self):
        return self.html_content.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_fetch_news_with_valid_html(monkeypatch):
    """Test fetch_news with valid HTML content."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <ul>
                    <li>
                        2023 - <span class="material-icons">add_circle</span>
                        <a href="/badge1">Badge 1</a> Nowa odznaka
                    </li>
                    <li>
                        2023 - <span class="material-icons">change_circle</span>
                        <a href="/badge2">Badge 2</a> Zmiana
                    </li>
                </ul>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()
    result = scraper.fetch_news()

    assert len(result) == 2
    assert result[0].change_type == "ADDITION"
    assert result[0].badge_name == "Badge 1"
    assert result[0].change_date_str == "2023"
    assert result[1].change_type == "CHANGE"
    assert result[1].badge_name == "Badge 2"


def test_fetch_news_with_network_error(monkeypatch):
    """Test fetch_news handles network errors."""

    def mock_urlopen(request, timeout=None):
        raise Exception("Network error")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()

    with pytest.raises(InfrastructureException) as exc_info:
        scraper.fetch_news()

    assert "Błąd sieci" in str(exc_info.value)


def test_fetch_news_with_missing_header(monkeypatch):
    """Test fetch_news raises exception when header is missing."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <p>No header here</p>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()

    with pytest.raises(InfrastructureException) as exc_info:
        scraper.fetch_news()

    assert "Nie znaleziono nagłówka" in str(exc_info.value)


def test_fetch_news_with_missing_list(monkeypatch):
    """Test fetch_news raises exception when list is missing."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <p>No list here</p>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()

    with pytest.raises(InfrastructureException) as exc_info:
        scraper.fetch_news()

    assert "Nie znaleziono listy" in str(exc_info.value)


def test_fetch_news_with_unknown_icon(monkeypatch):
    """Test fetch_news skips items with unknown icons."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <ul>
                    <li>
                        <span class="material-icons">unknown_icon</span>
                        <a href="/badge1">Badge 1:</a> 2023-01-01 - Unknown
                    </li>
                    <li>
                        <span class="material-icons">add_circle</span>
                        <a href="/badge2">Badge 2:</a> 2023-02-01 - Valid
                    </li>
                </ul>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()
    result = scraper.fetch_news()

    assert len(result) == 1
    assert result[0].badge_name == "Badge 2"


def test_fetch_news_with_missing_icon_or_link(monkeypatch):
    """Test fetch_news skips items with missing icon or link."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <ul>
                    <li>
                        <span class="material-icons">add_circle</span>
                        No link here
                    </li>
                    <li>
                        <a href="/badge2">Badge 2:</a> 2023-02-01 - No icon
                    </li>
                    <li>
                        <span class="material-icons">add_circle</span>
                        <a href="/badge3">Badge 3:</a> 2023-03-01 - Valid
                    </li>
                </ul>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()
    result = scraper.fetch_news()

    assert len(result) == 1
    assert result[0].badge_name == "Badge 3"


def test_source_url_constant():
    """Test that SOURCE_URL constant is set correctly."""
    assert BeautifulSoupNewsScraper.SOURCE_URL == "https://odznaki.org/zmiany/"


def test_fetch_news_with_non_string_href(monkeypatch):
    """Test fetch_news handles non-string href (line 85)."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <ul>
                    <li>
                        2023 - <span class="material-icons">add_circle</span>
                        <a href="">Badge 1</a> Nowa odznaka
                    </li>
                </ul>
            </body>
        </html>
        """
        return MockResponse(html)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    scraper = BeautifulSoupNewsScraper()
    result = scraper.fetch_news()

    assert len(result) == 1
    assert result[0].badge_name == "Badge 1"


def test_fetch_news_with_href_as_list(monkeypatch):
    """Test fetch_news handles href as list (line 81)."""

    def mock_urlopen(request, timeout=None):
        html = """
        <html>
            <body>
                <h2>Ostatnie 50 zmian</h2>
                <ul>
                    <li>
                        2023 - <span class="material-icons">add_circle</span>
                        <a href="/badge1">Badge 1</a> Nowa odznaka
                    </li>
                </ul>
            </body>
        </html>
        """
        return MockResponse(html)

    from unittest.mock import patch, MagicMock

    scraper = BeautifulSoupNewsScraper()

    with patch("urllib.request.urlopen", mock_urlopen):
        with patch("bs4.BeautifulSoup") as MockBS:
            mock_soup = MagicMock()
            MockBS.return_value = mock_soup

            mock_header = MagicMock()
            mock_soup.find.return_value = mock_header

            mock_list = MagicMock()
            mock_header.find_next_sibling.return_value = mock_list

            mock_item = MagicMock()
            mock_list.find_all.return_value = [mock_item]

            mock_icon = MagicMock()
            mock_icon.get_text.return_value = "add_circle"
            mock_item.find.side_effect = lambda *args, **kwargs: (
                mock_icon if args[0] == "span" else MagicMock(get_text=MagicMock(return_value="Badge 1"), get=MagicMock(return_value=["/badge1"]))
            )

            mock_item.get_text.return_value = "2023 - add_circle - Badge 1 Nowa odznaka"

            result = scraper.fetch_news()

    assert len(result) == 1
