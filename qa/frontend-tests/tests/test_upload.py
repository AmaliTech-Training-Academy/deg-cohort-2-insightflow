import os
from playwright.sync_api import Page, expect


class TestUploadPage:
    def _go(self, auth_page: Page, base_url: str) -> Page:
        auth_page.goto(f"{base_url}/uploads/new")
        expect(auth_page.locator("h1")).to_be_visible(timeout=10000)
        return auth_page

    # ── Page structure ─────────────────────────────────────────

    def test_heading_renders(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("h1")).to_have_text("New upload")

    def test_subtitle_renders(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(
            auth_page.locator("text=Import POS transactions from a CSV export")
        ).to_be_visible()

    def test_csv_data_source_badge_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("text=CSV File")).to_be_visible()

    def test_file_dropzone_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(
            auth_page.locator("text=Drop a file here, or click to browse")
        ).to_be_visible()

    def test_start_upload_button_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("button[type='submit']")).to_be_visible()

    def test_start_upload_button_disabled_without_file(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("button[type='submit']")).to_be_disabled()

    def test_file_requirements_card_visible(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        expect(auth_page.locator("text=File requirements")).to_be_visible()

    # ── CSV-only restriction ────────────────────────────────────

    def test_file_input_accepts_csv_only(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        file_input = auth_page.locator("input[type='file']")
        expect(file_input).to_have_attribute("accept", ".csv")

    def test_upload_button_enabled_after_csv_selected(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        tmp_path = "/tmp/test_upload.csv"
        with open(tmp_path, "w") as f:
            f.write("id,amount,date\n1,100.00,2026-01-01\n")
        auth_page.set_input_files("input[type='file']", tmp_path)
        expect(auth_page.locator("button[type='submit']")).to_be_enabled()
        os.remove(tmp_path)

    def test_selected_file_name_shown(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        tmp_path = "/tmp/sales_data.csv"
        with open(tmp_path, "w") as f:
            f.write("id,amount\n1,50\n")
        auth_page.set_input_files("input[type='file']", tmp_path)
        expect(auth_page.locator("text=sales_data.csv")).to_be_visible()
        os.remove(tmp_path)

    def test_remove_file_button_clears_selection(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        tmp_path = "/tmp/to_remove.csv"
        with open(tmp_path, "w") as f:
            f.write("id\n1\n")
        auth_page.set_input_files("input[type='file']", tmp_path)
        expect(auth_page.locator("text=to_remove.csv")).to_be_visible()
        auth_page.click("button[aria-label='Remove file']")
        expect(auth_page.locator("text=to_remove.csv")).not_to_be_visible()
        os.remove(tmp_path)

    # ── Navigation ──────────────────────────────────────────────

    def test_sidebar_shows_new_upload_as_active(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        active = auth_page.locator("nav a[aria-current='page']")
        expect(active).to_contain_text("New upload")

    def test_breadcrumb_shows_uploads_and_new_upload(self, auth_page: Page, base_url: str):
        self._go(auth_page, base_url)
        crumb = auth_page.locator("nav[aria-label='Breadcrumb']")
        expect(crumb).to_contain_text("Uploads")
        expect(crumb).to_contain_text("New upload")
