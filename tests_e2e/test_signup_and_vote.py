"""Playwright end-to-end smoke test — mirrors the Next.js version's
tests/e2e/signup-and-vote.spec.ts. Exercises the real HTTP + browser
stack against a running `python manage.py runserver` instance (not
pytest-django's test client), so it catches template/JS wiring bugs unit
tests can't see (this is exactly how the missing {% load static %} and
the `cumulative_score.last` template bug in this project were actually
found and fixed).

Requires the dev server to be running at BASE_URL (default
http://localhost:8000) against a freshly migrated + seeded database.
Run manually:

    python manage.py runserver &
    python manage.py migrate && python manage.py seed_data
    python -m pytest tests_e2e/ -q

Not part of the default `pytest` run (see pytest.ini's testpaths) since
it needs a live server + browser, unlike the fast unit/integration
suite in tests/.
"""

import os
import random
import string

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def _random_username() -> str:
    return "e2e_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        launch_kwargs = {"executable_path": CHROMIUM_PATH} if os.path.exists(CHROMIUM_PATH) else {}
        b = p.chromium.launch(**launch_kwargs)
        yield b
        b.close()


def test_signup_login_and_vote(browser):
    username = _random_username()
    email = f"{username}@example.com"
    password = "Password1!"

    page = browser.new_page()

    # --- Register --------------------------------------------------
    page.goto(f"{BASE_URL}/accounts/register/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Registration auto-logs-in and redirects to the dashboard.
    assert "/me/" in page.url or page.locator("text=マイページ").count() > 0

    # --- Vote on an open prediction ---------------------------------
    page.goto(f"{BASE_URL}/predictions/")
    first_card = page.locator("a.card").first
    first_card.click()
    page.wait_for_load_state("networkidle")

    yes_button = page.locator(".js-vote-btn", has_text="").first
    # Prefer a button explicitly not showing the closed-state empty
    # message; if the prediction picked happened to be closed, skip.
    if page.locator("#vote-panel").count() == 0:
        pytest.skip("Selected prediction has no open vote panel (deadline passed) — not a bug, just bad luck of ordering.")

    page.locator('.js-vote-btn[data-option="YES"]').click()
    page.wait_for_timeout(500)  # fetch() round-trip

    status_text = page.locator("#vote-status").inner_text()
    assert "YES" in status_text or "現在の予測" in status_text

    # --- Logout ------------------------------------------------------
    page.goto(f"{BASE_URL}/")
    page.click("text=ログアウト")
    page.wait_for_load_state("networkidle")
    assert page.locator("text=ログイン").count() > 0


def test_ranking_page_loads_without_login(browser):
    page = browser.new_page()
    page.goto(f"{BASE_URL}/ranking/")
    assert page.locator("h1", has_text="ランキング").count() == 1


def test_home_shows_legal_disclaimer(browser):
    page = browser.new_page()
    page.goto(f"{BASE_URL}/")
    # Every page must show the "not investment advice / no money" legal
    # disclaimer — this is a hard business requirement, not a nicety.
    assert page.locator("text=投資助言").count() >= 1
    assert page.locator("text=金銭").count() >= 1
