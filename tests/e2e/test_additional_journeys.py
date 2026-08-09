"""Dodatkowe scenariusze E2E: Szczegóły odznaki, obiekt, profil, ranking, katalog."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_badge_detail_page_loads_from_catalog(auth_page: Page):
    """Z katalogu można przejść do szczegółów odznaki i zobaczyć sekcję postępu."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_links = auth_page.locator("[data-testid^='link-badge-detail-']")
    expect(badge_links.first).to_be_visible()
    badge_links.first.click()

    expect(auth_page).to_have_url(re.compile(r".*/badge/"))

    progress_section = auth_page.locator("[data-testid='badge-progress-section']")
    not_subscribed_heading = auth_page.locator("text='Nie zdobywasz tej odznaki'")
    if progress_section.is_visible():
        expect(auth_page.locator("[data-testid='progress-text']")).to_be_visible()
    else:
        expect(not_subscribed_heading).to_be_visible()


@pytest.mark.e2e
def test_badge_detail_objects_list_is_visible(auth_page: Page):
    """W szczegółach odznaki widoczna jest lista obiektów do zdobycia."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_links = auth_page.locator("[data-testid^='link-badge-detail-']")
    expect(badge_links.first).to_be_visible()
    badge_links.first.click()

    expect(auth_page).to_have_url(re.compile(r".*/badge/"))
    object_items = auth_page.locator("[data-testid^='object-list-item-']")
    expect(object_items.first).to_be_visible()


@pytest.mark.e2e
def test_object_detail_page_loads_from_badge(auth_page: Page):
    """Z szczegółów odznaki można przejść do szczegółów obiektu."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_links = auth_page.locator("[data-testid^='link-badge-detail-']")
    expect(badge_links.first).to_be_visible()
    badge_links.first.click()

    expect(auth_page).to_have_url(re.compile(r".*/badge/"))
    object_link = auth_page.locator("[data-testid^='object-list-item-'] a").first
    if object_link.is_visible():
        object_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/object/\d+/"))


@pytest.mark.e2e
def test_object_detail_shows_ascent_button_and_history(auth_page: Page):
    """Strona obiektu zawiera przycisk zalogowania wejścia i sekcję historii."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_links = auth_page.locator("[data-testid^='link-badge-detail-']")
    expect(badge_links.first).to_be_visible()
    badge_links.first.click()

    expect(auth_page).to_have_url(re.compile(r".*/badge/"))
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
def test_navigation_from_ranking_to_object_detail(auth_page: Page):
    """Z rankingu celów można przejść do szczegółów obiektu."""
    auth_page.goto("/ranking/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/"))

    object_link = auth_page.locator("[data-testid^='link-ranking-object-']").first
    if object_link.is_visible():
        object_link.click()
        expect(auth_page).to_have_url(re.compile(r".*/object/\d+/"))


@pytest.mark.e2e
def test_catalog_shows_badges_and_subscribe_button(auth_page: Page):
    """Katalog odznak wyświetla listę odznak z przyciskiem subskrypcji."""
    auth_page.goto("/catalog/")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    badge_cards = auth_page.locator("[data-testid^='badge-card-']")
    expect(badge_cards.first).to_be_visible()

    subscribe_buttons = auth_page.locator("[data-testid^='btn-subscribe-']")
    expect(subscribe_buttons.first).to_be_visible()


@pytest.mark.e2e
def test_ranking_page_shows_object_links(auth_page: Page):
    """Ranking celów zawiera linki do szczegółów obiektów."""
    auth_page.goto("/ranking/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/"))

    object_links = auth_page.locator("[data-testid^='link-ranking-object-']")
    expect(object_links.first).to_be_visible()


@pytest.mark.e2e
def test_region_ranking_page_loads(auth_page: Page):
    """Skumulowany ranking regionów ładuje się z domyślnym poziomem."""
    auth_page.goto("/ranking/regions/")
    expect(auth_page).to_have_url(re.compile(r".*/ranking/regions/"))

    expect(auth_page.locator("text=Ranking Regionów")).to_be_visible()


@pytest.mark.e2e
def test_navigation_bar_links_are_visible(auth_page: Page):
    """Główna nawigacja zawiera wszystkie kluczowe linki."""
    auth_page.goto("/")
    expect(auth_page).to_have_url(re.compile(r".*/"))

    expect(auth_page.locator("text=Pulpit Mapy")).to_be_visible()
    expect(auth_page.locator("text=Ranking Celów")).to_be_visible()
    expect(auth_page.locator("text=Katalog Odznak")).to_be_visible()
    expect(auth_page.locator("text=📦 Moja Logistyka")).to_be_visible()
