import json
from os import getenv

import pytest

_AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"


@pytest.mark.e2e
def test_axe_root_page_has_no_accessibility_violations(page):
    base_url = getenv("EUIE_BASE_URL", "http://localhost:8009")
    page.goto(f"{base_url}/")
    page.add_script_tag(url=_AXE_CDN)
    violations = page.evaluate(
        "() => new Promise(resolve =>"
        " window.axe.run({ runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } },"
        " (err, results) => resolve(results.violations)))"
    )
    assert not violations, json.dumps(violations, indent=2, default=str)[:2000]
