"""AUDYT-149: Test autentycznej ścieżki logowania (bez bypassu ciasteczka).

Weryfikuje:
  1. Strona `/accounts/login/` renderuje widoczny przycisk Google (data-testid).
  2. Niezalogowany turysta dostaje 302 na chronionej ścieżce `/profile/`.
  3. Brak `DJANGO_SECRET_KEY` / `GOOGLE_CLIENT_ID` w renderowanym HTML.
"""

import os
import sys

import pytest
import requests
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8009")
LOGIN_PATH = "/accounts/login/"


def test_login_page_renders_google_button(page: Page) -> None:
    """Strona logowania /accounts/login/ musi pokazywać przycisk Google OAuth."""
    page.context.clear_cookies()
    resp = page.goto(f"{BASE_URL}{LOGIN_PATH}", wait_until="domcontentloaded", timeout=15000)
    assert resp is not None, "Failed to load /accounts/login/"
    assert resp.status == 200, f"Expected 200, got {resp.status} at {resp.url}"
    title = page.title()
    print(f"[DEBUG] title={title!r} url={page.url!r}", file=sys.stderr, flush=True)
    html = page.content()
    html_has_btn = "btn-login-google" in html
    btn = page.locator("button[data-testid='btn-login-google']")
    btn_count = btn.count()
    print(f"[DEBUG] btn_count={btn_count} html_has_btn={html_has_btn}", file=sys.stderr, flush=True)
    expect(btn).to_be_visible(timeout=10000)
    assert btn_count == 1


def test_login_page_has_no_raw_secrets(page: Page) -> None:
    """HTML strony logowania nie może wyciekać secretów."""
    page.goto(f"{BASE_URL}{LOGIN_PATH}", wait_until="domcontentloaded", timeout=15000)
    html = page.content()
    assert "DJANGO_SECRET_KEY" not in html
    assert "GOOGLE_CLIENT_ID" not in html


def test_unauthenticated_user_redirected_from_protected_route() -> None:
    """Turysta bez sesji → 302 redirect z /profile/ na /accounts/login/.

    Czyste `requests.get` z `allow_redirects=False` i brak cookies
    symuluje anonimowego użytkownika — nie dzieli sesji z Playwright.
    """
    resp = requests.get(f"{BASE_URL}/profile/", allow_redirects=False, timeout=10)
    assert resp.status_code == 302, f"Expected 302, got {resp.status_code} body={resp.text[:200]}"
    loc = resp.headers.get("location", "")
    assert "accounts/login" in loc
