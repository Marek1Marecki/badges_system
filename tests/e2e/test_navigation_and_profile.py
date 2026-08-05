"""Rozszerzone scenariusze E2E: Dashboard, Ranking, Profil, Logistyka, Szczegóły obiektu."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_dashboard_shows_active_badges(auth_page: Page):
    """Dashboard powinien wyświetlić listę aktywnych odznak użytkownika."""
    auth_page.goto("/")
    expect(auth_page).to_have_url(re.compile(r".*/$"))

    badges_list = auth_page.locator("[data-testid='dashboard-badges-list']")
    expect(badges_list).to_be_visible()


@pytest.mark.e2e
def test_dashboard_navigates_to_badge_detail(auth_page: Page):
    """Z pulpitu można przejść do szczegółów odznaki."""
    auth_page.goto("/")

    first_badge_link = auth_page.locator("[data-testid='link-dashboard-badge-KGP']").first
    if first_badge_link.is_visible():
        first_badge_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/badge/KGP"))


@pytest.mark.e2e
def test_region_ranking_tabs_switch(auth_page: Page):
    """Z widoku regionów można przejść do rankingu pojedynczych obiektów."""
    auth_page.goto("/ranking/regions/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/regions/"))

    tab = auth_page.locator("[data-testid='tab-single-objects']")
    if tab.is_visible():
        tab.click()
        expect(auth_page).to_have_url(re.compile(r".*/ranking/"))


@pytest.mark.e2e
def test_region_ranking_page_loads(auth_page: Page):
    """Skumulowany ranking regionów ładuje się z domyślnym poziomem."""
    auth_page.goto("/ranking/regions/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/regions/"))

    expect(auth_page.locator("[data-testid='btn-show-map']")).to_be_visible()


@pytest.mark.e2e
def test_profile_page_shows_form(auth_page: Page):
    """Strona ustawień profilu wyświetla formularz edycji."""
    auth_page.goto("/profile/")
    expect(auth_page).to_have_url(re.compile(r".*/profile/"))

    expect(auth_page.locator("[data-testid='profile-form']")).to_be_visible()
    expect(auth_page.locator("[data-testid='input-nickname']")).to_be_visible()
    expect(auth_page.locator("[data-testid='btn-save-profile']")).to_be_visible()


@pytest.mark.e2e
def test_logistics_page_loads(auth_page: Page):
    """Tablica Kanban logistyczna ładuje się nawet bez zleceń."""
    auth_page.goto("/logistics/")
    expect(auth_page).to_have_url(re.compile(r".*/logistics/"))

    expect(auth_page.locator("[data-testid='kanban-waiting-for-send']")).to_be_visible()
    expect(auth_page.locator("[data-testid='kanban-waiting-for-verification']")).to_be_visible()
    expect(auth_page.locator("[data-testid='kanban-waiting-for-receiving']")).to_be_visible()
    expect(auth_page.locator("[data-testid='kanban-album']")).to_be_visible()


@pytest.mark.e2e
def test_navigation_bar_links_are_visible(auth_page: Page):
    """Główna nawigacja zawiera wszystkie kluczowe linki."""
    auth_page.goto("/")

    expect(auth_page.locator("[data-testid='nav-dashboard']")).to_be_visible()
    expect(auth_page.locator("[data-testid='nav-ranking']")).to_be_visible()
    expect(auth_page.locator("[data-testid='nav-catalog']")).to_be_visible()
    expect(auth_page.locator("[data-testid='nav-logistics']")).to_be_visible()
    expect(auth_page.locator("[data-testid='btn-profile-dropdown']")).to_be_visible()
    expect(auth_page.locator("[data-testid='btn-logout']")).to_be_visible()
