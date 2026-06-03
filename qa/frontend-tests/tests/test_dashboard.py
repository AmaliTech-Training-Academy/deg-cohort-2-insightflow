from playwright.sync_api import Page, expect


class TestDashboardPage:
    def test_unauthenticated_redirects_to_login(self, page: Page, base_url: str):
        page.goto(f"{base_url}/dashboard")
        expect(page).to_have_url(f"{base_url}/login", timeout=6000)

    def test_dashboard_heading_renders(self, auth_page: Page):
        expect(auth_page.locator("h1")).to_have_text("Dashboard")

    def test_stat_cards_render(self, auth_page: Page):
        expect(auth_page.locator("text=Jobs Today")).to_be_visible(timeout=10000)
        expect(auth_page.locator("text=Successful")).to_be_visible()
        expect(auth_page.locator("text=Failed")).to_be_visible()
        expect(auth_page.locator("text=Records Ingested")).to_be_visible()

    def test_source_health_table_renders(self, auth_page: Page):
        expect(auth_page.locator("text=Data Source Health")).to_be_visible(
            timeout=15000
        )
        expect(auth_page.locator("th:has-text('Source')")).to_be_visible()
        expect(auth_page.locator("th:has-text('Status')")).to_be_visible()

    def test_sidebar_shows_dashboard_as_active(self, auth_page: Page):
        active = auth_page.locator("nav a[aria-current='page']")
        expect(active).to_contain_text("Dashboard")

    def test_breadcrumb_shows_dashboard(self, auth_page: Page):
        expect(auth_page.locator("nav[aria-label='Breadcrumb']")).to_contain_text(
            "Dashboard"
        )

    def test_theme_toggle_button_visible(self, auth_page: Page):
        expect(auth_page.locator("button[aria-label*='mode']")).to_be_visible()
