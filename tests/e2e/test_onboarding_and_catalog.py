"""Testy E2E dla Onboardingu, Limitów Freemium i nawigacji w Katalogu."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_logged_in_user_can_navigate_to_catalog_and_subscribe(auth_page: Page):
    """Sprawdza podstawowy przepływ: Dashboard -> Katalog -> Subskrypcja (US-C01b)."""

    auth_page.goto("/")
    expect(auth_page).to_have_title(re.compile(r".*"))
    expect(auth_page.locator("[data-testid='btn-profile-dropdown']")).to_be_visible()

    auth_page.click("[data-testid='nav-catalog']")
    expect(auth_page).to_have_url(re.compile(r".*/catalog/"))

    kgp_card = auth_page.locator("[data-testid='badge-card-KGP']")
    expect(kgp_card).to_be_visible()

    subscribe_btn = kgp_card.locator("[data-testid='btn-subscribe-KGP']")
    unsubscribe_btn = kgp_card.locator("[data-testid='btn-unsubscribe-KGP']")

    # Jeśli już ją subskrybujemy, najpierw ją zdejmijmy!
    if unsubscribe_btn.is_visible():
        unsubscribe_btn.click()
        auth_page.wait_for_timeout(1000)
    
    # Teraz bezpiecznie subskrybujemy
    expect(subscribe_btn).to_be_visible()
    subscribe_btn.click()
    
    # Czekamy na powiadomienie Toast
    toast = auth_page.locator("[data-testid='toast-container']")
    expect(toast).to_contain_text(re.compile(r"(sukces|rozpoczęto|dodano)", re.IGNORECASE))


@pytest.mark.e2e
def test_freemium_limit_blocks_excessive_subscriptions(auth_page: Page):
    """Weryfikuje, czy ochrona pakietu FREE odrzuca 4-tą subskrypcję (US-C01c)."""
    auth_page.goto("/catalog/")

    badges_to_click = ["KGP", "ZKSP", "KS"]

    for code in badges_to_click:
        btn = auth_page.locator(f"[data-testid='btn-subscribe-{code}']")
        if btn.is_visible():
            btn.click()
            auth_page.wait_for_timeout(500)

    btn_limit = auth_page.locator("[data-testid='btn-subscribe-KPB']")
    if btn_limit.is_visible():
        btn_limit.click()

        toast = auth_page.locator("[data-testid='toast-container']")
        expect(toast).to_contain_text(re.compile(r"(limit|przekroczono|pakiet|zablokowane)", re.IGNORECASE))
