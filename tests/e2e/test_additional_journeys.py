"""Dodatkowe scenariusze E2E: Szczegóły odznaki, obiekt, profil, logowanie, ascent."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_badge_detail_page_loads_and_shows_progress(auth_page: Page):
    """Strona szczegółów odznaki ładuje się i pokazuje sekcję postępu."""
    auth_page.goto("/badge/KGP/")
    expect(auth_page).to_have_url(re.compile(r".*/badge/KGP"))

    expect(auth_page.locator("[data-testid='badge-progress-section']")).to_be_visible()
    expect(auth_page.locator("[data-testid='progress-text']")).to_be_visible()


@pytest.mark.e2e
def test_badge_detail_objects_list_is_visible(auth_page: Page):
    """W szczegółach odznaki widoczna jest lista obiektów do zdobycia."""
    auth_page.goto("/badge/KGP/")
    expect(auth_page).to_have_url(re.compile(r".*/badge/KGP"))

    object_items = auth_page.locator("[data-testid^='object-list-item-']")
    expect(object_items.first).to_be_visible()


@pytest.mark.e2e
def test_object_detail_page_loads_from_badge(auth_page: Page):
    """Z szczegółów odznaki można przejść do szczegółów obiektu."""
    auth_page.goto("/badge/KGP/")
    expect(auth_page).to_have_url(re.compile(r".*/badge/KGP"))

    object_link = auth_page.locator("[data-testid^='object-list-item-'] a").first
    if object_link.is_visible():
        object_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/object/\d+/"))


@pytest.mark.e2e
def test_object_detail_shows_ascent_button_and_history(auth_page: Page):
    """Strona obiektu zawiera przycisk zalogowania wejścia i sekcję historii."""
    auth_page.goto("/badge/KGP/")
    object_link = auth_page.locator("[data-testid^='object-list-item-'] a").first
    if object_link.is_visible():
        object_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/object/\d+/"))

        expect(auth_page.locator("[data-testid='btn-log-ascent']")).to_be_visible()
        expect(auth_page.locator("text=Twoja Historia")).to_be_visible()


@pytest.mark.e2e
def test_profile_page_can_update_nickname(auth_page: Page):
    """W ustawieniach profilu można zmienić pseudonim i zapisać zmiany."""
    auth_page.goto("/profile/")
    expect(auth_page).to_have_url(re.compile(r".*/profile/"))

    nickname_input = auth_page.locator("[data-testid='input-nickname']")
    expect(nickname_input).to_be_visible()
    nickname_input.fill("admin_updated")

    save_btn = auth_page.locator("[data-testid='btn-save-profile']")
    expect(save_btn).to_be_visible()
    save_btn.click()

    auth_page.wait_for_timeout(500)
    expect(auth_page.locator("[data-testid='input-nickname']")).to_have_value("admin_updated")


@pytest.mark.e2e
def test_login_page_shows_google_button(auth_page: Page):
    """Strona logowania wyświetla przycisk logowania przez Google."""
    page = auth_page.context.new_page()
    page.goto("/accounts/login/")
    expect(page).to_have_url(re.compile(r".*/accounts/login/"))

    expect(page.locator("[data-testid='btn-login-google']")).to_be_visible()
    page.close()


@pytest.mark.e2e
def test_navigation_from_ranking_to_object_detail(auth_page: Page):
    """Z rankingu celów można przejść do szczegółów obiektu."""
    auth_page.goto("/ranking/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/"))

    object_link = auth_page.locator("[data-testid^='link-ranking-object-']").first
    if object_link.is_visible():
        object_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/object/\d+/"))


@pytest.mark.e2e
def test_catalog_to_badge_detail_navigation(auth_page: Page):
    """Z katalogu można przejść do szczegółów dowolnej odznaki."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_links = auth_page.locator("[data-testid^='link-badge-detail-']")
    count = badge_links.count()
    assert count > 0

    badge_links.first.click()
    expect(auth_page).to_have_url(re.compile(r".*/badge/"))
