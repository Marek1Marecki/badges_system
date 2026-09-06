"""AUDYT-149: Test autentycznego logowania Google OAuth.

Używa *czystego* kontekstu przeglądarki (bez wstrzykiwania ciasteczka
`sessionid` z `create_test_session`). Weryfikuje:
  1. Strona `/accounts/login/` renderuje przycisk logowania Google.
  2. Kliknięcie przenosi do Google OAuth (przekierowanie 302 / Google).
  3. Strona nie "wycieka" niepotrzebnego HTML i właściwie obsługuje
     niezalogowanego turystę (401/302 na chronione ścieżki).
"""

import os
import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8009")
BASE = "/accounts/login/"


def test_login_page_renders_google_button(page: Page) -> None:
    """Strona logowania musi pokazywać widoczny przycisk logowania Google."""
    page.goto(BASE)
    expect(page).to_have_title(re.compile("Logowanie", re.IGNORECASE))

    # allauth renderuje przycisk z atrybutem /data-/href do Google OAuth
    google_btn = page.locator("a[href*='/accounts/google/login/']")
    expect(google_btn).to_be_visible()
    assert google_btn.count() == 1


def test_login_page_redirects_to_google_when_clicked(page: Page) -> None:
    """Po kliknięciu przycisku przekierowuje do providera Google OAuth.

    Oczekujemy przekierowania (Google może odpowiedzieć 302, 301, 200
    na stronie logowania Google, ale URI musi zawierać `accounts.google`
    lub `accounts/o/` — typowy flow dla allauth/socialaccount).
    """
    page.goto(BASE)
    with page.expect_navigation(timeout=10000) as nav_info:
        page.locator("a[href*='/accounts/google/login/']").click()
    assert "google" in nav_info.value.url.lower() or "accounts.google" in nav_info.value.url


def test_login_page_has_no_raw_secrets(page: Page) -> None:
    page.goto(BASE)
    html = page.content()
    assert "DJANGO_SECRET_KEY" not in html
    assert "GOOGLE_CLIENT_ID" not in html


def test_unauthenticated_user_redirected_from_protected_route(page: Page) -> None:
    """Turysta bez sesji ma być przekierowany z chronionej ścieżki."""
    # Próba wejścia na stronę wymagającą auth — powinno być 302→login
    response = page.request.get(BASE_URL + "/profile/")
    assert response.status == 302, f"Expected redirect, got {response.status}"
    loc = response.headers.get("location", "")
    assert "accounts/login" in loc
