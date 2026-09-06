"""AUDYT-149: Test autentycznej ścieżki logowania (bez bypassu ciasteczka).

Używa *czystego* kontekstu przeglądarki (bez wstrzykiwania `sessionid`
z `create_test_session`) i globalnego APIRequestContext (bez cookies).
Weryfikuje:
  1. Strona `/accounts/login/` renderuje widoczny przycisk Google (data-testid).
  2. Niezalogowany turysta dostaje 302 na chronionej ścieżce `/profile/`.
  3. Brak `DJANGO_SECRET_KEY` / `GOOGLE_CLIENT_ID` w renderowanym HTML.
"""

import os
from typing import Any

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8009")
LOGIN_PATH = "/accounts/login/"


def test_login_page_renders_google_button(page: Page) -> None:
    """Strona logowania /accounts/login/ musi pokazywać przycisk Google OAuth."""
    page.goto(BASE_URL + LOGIN_PATH)
    # Szablon allauth: <h2>Witaj na szlaku! ⛰️</h2>
    expect(page.locator("h2")).to_contain_text("szlaku")
    btn = page.locator("button[data-testid='btn-login-google']")
    expect(btn).to_be_visible()
    assert btn.count() == 1


def test_login_page_has_no_raw_secrets(page: Page) -> None:
    """HTML strony logowania nie może wyciekać secretów."""
    page.goto(BASE_URL + LOGIN_PATH)
    html = page.content()
    assert "DJANGO_SECRET_KEY" not in html
    assert "GOOGLE_CLIENT_ID" not in html


def test_unauthenticated_user_redirected_from_protected_route(playwright: Any) -> None:
    """Turysta bez sesji → 302 redirect z /profile/ na /accounts/login/.

    Globalny `playwright.request.new_context()` nie dzieli ciasteczek
    z browser context → rzeczywiście anonimowy request.
    """
    ctx = playwright.request.new_context()  # type: ignore[no-any-return]
    try:
        resp = ctx.get(f"{BASE_URL}/profile/")
        assert resp.status == 302, f"Expected 302, got {resp.status}"
        loc = resp.headers.get("location", "")
        assert "accounts/login" in loc
    finally:
        ctx.dispose()
