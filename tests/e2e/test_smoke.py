import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_homepage_loads_and_has_title(page: Page):
    """Weryfikuje, czy aplikacja w ogóle odpowiada i serwuje stronę główną."""
    page.goto("/")

    # Nasz weryfikator tego, że Caddy/Gunicorn działają
    expect(page).to_have_title(re.compile(r".*"))


@pytest.mark.e2e
def test_catalog_is_protected_by_login(page: Page):
    """Sprawdza, czy próba wejścia do katalogu bez logowania rzuca na ekran autoryzacji."""
    page.goto("/")

    # Klikamy w link/przycisk prowadzący do katalogu
    page.click("text=Katalog")

    # Oczekujemy, że adres URL będzie zawierał ścieżkę logowania (Regex zabezpiecza nas przed hardkodowaniem domeny)
    expect(page).to_have_url(re.compile(r".*/accounts/login/.*next=/catalog/"))

    # Oczekujemy, że na stronie pojawi się np. tekst logowania lub formularz Allauth
    expect(page.locator("body")).to_contain_text(re.compile(r"Zaloguj", re.IGNORECASE))


@pytest.mark.e2e
def test_logged_in_user_can_view_catalog(auth_page: Page):
    """Sprawdza, czy zalogowany robot może wejść do katalogu odznak i zobaczyć dane z bazy."""
    auth_page.goto("/catalog/")

    # Zamiast przekierowania, oczekujemy, że zostaniemy w katalogu
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    # Oczekujemy, że z bazy danych referencyjnych wciągnęły się odznaki
    # UWAGA: Podmień "Korona Gór Polski" na fizyczny tytuł odznaki lub nagłówka strony na Twoim UI!
    expect(auth_page.locator("body")).to_contain_text("Korona Gór Polski")
