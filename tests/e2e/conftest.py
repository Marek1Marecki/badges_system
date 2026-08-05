import os
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8009")


def get_session_cookie(username: str) -> str:
    cmd = ["python", "manage.py", "create_test_session", username]
    result = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=True, cwd=str(Path(__file__).resolve().parent.parent.parent)
    )
    return result.stdout.strip().split("\n")[-1]


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Konfiguracja przeglądarki (Rozmiar i adres docelowy)."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "base_url": BASE_URL,
    }


@pytest.fixture
def logged_in_context(context: BrowserContext) -> BrowserContext:
    """Fixture wstrzykująca ciastko sesji do przeglądarki Playwright."""

    # Kradniemy sesję dla domyślnego użytkownika admin (założonego w bootstrap.sh)
    session_id = get_session_cookie("admin")

    # Dodajemy ciastko do przeglądarki
    context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": session_id,
                "domain": "localhost",
                "path": "/",
            }
        ]
    )

    return context


@pytest.fixture
def auth_page(logged_in_context: BrowserContext) -> Page:
    """Dostarcza w pełni zalogowaną stronę do testów."""
    page = logged_in_context.new_page()
    yield page
    page.close()


@pytest.fixture
def page(context: BrowserContext) -> Page:
    """Dostarcza standardową (niezalogowaną) stronę do testów dymnych."""
    page = context.new_page()
    yield page
    page.close()
