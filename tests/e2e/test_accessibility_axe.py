import json
from os import getenv

import pytest
from playwright.sync_api import Page

_AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"
_BASE_URL = getenv("EUIE_BASE_URL", "http://localhost:8009")


def _check_accessibility(page: Page, url: str) -> None:
    page.goto(url)
    page.add_script_tag(url=_AXE_CDN)
    violations = page.evaluate(
        "() => new Promise(resolve =>"
        " window.axe.run({ runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } },"
        " (err, results) => resolve(results.violations)))"
    )
    assert not violations, json.dumps(violations, indent=2, default=str)[:2000]


@pytest.mark.e2e
def test_axe_root_page_has_no_accessibility_violations(page: Page):
    _check_accessibility(page, f"{_BASE_URL}/")


@pytest.mark.e2e
def test_axe_login_page_has_no_accessibility_violations(page: Page):
    _check_accessibility(page, f"{_BASE_URL}/accounts/login/")


@pytest.mark.e2e
def test_axe_dashboard_has_no_accessibility_violations(auth_page: Page):
    _check_accessibility(auth_page, f"{_BASE_URL}/")


@pytest.mark.e2e
def test_axe_catalog_has_no_accessibility_violations(auth_page: Page):
    _check_accessibility(auth_page, f"{_BASE_URL}/catalog/")


@pytest.mark.e2e
def test_axe_profile_settings_has_no_accessibility_violations(auth_page: Page):
    _check_accessibility(auth_page, f"{_BASE_URL}/profile/")


@pytest.mark.e2e
def test_axe_ranking_has_no_accessibility_violations(auth_page: Page):
    _check_accessibility(auth_page, f"{_BASE_URL}/ranking/")


@pytest.mark.e2e
def test_axe_404_page_has_no_accessibility_violations(page: Page):
    _check_accessibility(page, f"{_BASE_URL}/nonexistent-page-404/")
