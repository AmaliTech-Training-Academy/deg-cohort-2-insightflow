from playwright.sync_api import Page, expect


def _wait_dark(page: Page, timeout_ms: int = 5000) -> None:
    page.wait_for_selector("html.dark", timeout=timeout_ms)


def _wait_light(page: Page, timeout_ms: int = 5000) -> None:
    page.wait_for_function(
        "!document.documentElement.classList.contains('dark')",
        timeout=timeout_ms,
    )


class TestThemeToggle:
    # ── Login page (unauthenticated — uses plain `page`) ───────

    def test_theme_toggle_exists_on_login(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        expect(page.locator("button[aria-label='Toggle dark mode']")).to_be_visible()

    def test_login_toggle_switches_to_dark(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        _wait_light(page)
        page.click("button[aria-label='Toggle dark mode']")
        _wait_dark(page)

    def test_login_toggle_switches_back_to_light(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        _wait_light(page)
        page.click("button[aria-label='Toggle dark mode']")
        _wait_dark(page)
        page.click("button[aria-label='Toggle dark mode']")
        _wait_light(page)

    # ── App header (authenticated — uses `auth_page`) ──────────

    def test_theme_toggle_exists_in_app_header(self, auth_page: Page):
        expect(auth_page.locator("header button[aria-label*='mode']")).to_be_visible()

    def test_app_toggle_switches_to_dark(self, auth_page: Page):
        _wait_light(auth_page)
        auth_page.click("header button[aria-label*='mode']")
        _wait_dark(auth_page)

    def test_app_toggle_switches_back_to_light(self, auth_page: Page):
        _wait_light(auth_page)
        auth_page.click("header button[aria-label*='mode']")
        _wait_dark(auth_page)
        auth_page.click("header button[aria-label*='mode']")
        _wait_light(auth_page)

    def test_theme_persists_across_navigation(self, auth_page: Page, base_url: str):
        _wait_light(auth_page)
        auth_page.click("header button[aria-label*='mode']")
        _wait_dark(auth_page)
        auth_page.goto(f"{base_url}/uploads/new")
        _wait_dark(auth_page)
