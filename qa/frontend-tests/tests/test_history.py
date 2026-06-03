from playwright.sync_api import Page, expect


class TestIngestionHistoryPage:
    def _go(self, auth_page: Page, base_url: str) -> Page:
        auth_page.goto(f"{base_url}/uploads/history")
        expect(auth_page.locator("h1")).to_be_visible(timeout=10000)
        return auth_page

    def test_heading_renders(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("h1")).to_have_text("Ingestion history")

    def test_new_upload_button_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.get_by_role("link", name="New Upload", exact=True)).to_be_visible()

    def test_table_columns_render(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        for col in ["File", "Source", "Status", "Records", "Started"]:
            expect(auth_page.locator(f"th:has-text('{col}')")).to_be_visible(timeout=10000)

    def test_table_has_rows(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("tbody tr").first).to_be_visible(timeout=10000)
        expect(auth_page.locator("tbody tr")).not_to_have_count(0)

    def test_status_badges_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("tbody tr").first).to_be_visible(timeout=10000)
        expect(auth_page.locator("tbody td span").first).to_be_visible()

    def test_new_upload_button_navigates_to_upload(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        auth_page.get_by_role("link", name="New Upload", exact=True).click()
        expect(auth_page).to_have_url(f"{base_url}/uploads/new")

    def test_sidebar_shows_ingestion_history_as_active(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        active = auth_page.locator("nav a[aria-current='page']")
        expect(active).to_contain_text("Ingestion history")

    def test_breadcrumb_shows_ingestion_history(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("nav[aria-label='Breadcrumb']")).to_contain_text("Ingestion history")
