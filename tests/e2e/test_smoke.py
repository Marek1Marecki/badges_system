import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_homepage_loads_and_has_title(page: Page):
    """Weryfikuje, czy aplikacja w ogóle odpowiada i serwuje stronę główną."""
    page.goto("/")

    expect(page).to_have_title(re.compile(r".*"))


@pytest.mark.e2e
def test_catalog_is_protected_by_login(page: Page):
    """Sprawdza, czy próba wejścia do katalogu bez logowania rzuca na ekran autoryzacji."""
    page.goto("/")

    page.click("text=Katalog")

    expect(page).to_have_url(re.compile(r".*/accounts/login/.*next=/catalog/"))
    expect(page.locator("body")).to_contain_text(re.compile(r"Zaloguj", re.IGNORECASE))


@pytest.mark.e2e
def test_logged_in_user_can_view_catalog(auth_page: Page):
    """Sprawdza, czy zalogowany robot może wejść do katalogu odznak."""
    auth_page.goto("/catalog/")

    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))
    expect(auth_page.locator("body")).to_contain_text("Katalog Odznak")
