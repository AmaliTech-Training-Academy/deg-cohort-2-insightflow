from playwright.sync_api import Page, expect


class TestLoginPage:
    def test_heading_and_subtitle_render(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        expect(page.locator("h1")).to_have_text("Sign in")
        expect(
            page.locator("text=Operations console for the retail data pipeline.")
        ).to_be_visible()

    def test_insightflow_logo_visible(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        expect(page.locator("text=InsightFlow").first).to_be_visible()

    def test_email_field_accepts_input(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.fill("#email", "user@insightflow.io")
        expect(page.locator("#email")).to_have_value("user@insightflow.io")

    def test_password_field_is_masked_by_default(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        expect(page.locator("#password")).to_have_attribute("type", "password")

    def test_password_show_hide_toggle(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.fill("#password", "secret123")
        page.click("button[aria-label='Show password']")
        expect(page.locator("#password")).to_have_attribute("type", "text")
        page.click("button[aria-label='Hide password']")
        expect(page.locator("#password")).to_have_attribute("type", "password")

    def test_empty_submission_shows_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.click("button[type='submit']")
        expect(
            page.locator("text=Please enter your email and password.")
        ).to_be_visible()

    def test_forgot_password_link_goes_to_correct_page(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.click("text=Forgot password?")
        expect(page).to_have_url(f"{base_url}/forgot-password")

    def test_register_link_goes_to_correct_page(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.click("text=Register")
        expect(page).to_have_url(f"{base_url}/register")

    def test_successful_login_redirects_to_dashboard(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.fill("#email", "user@insightflow.io")
        page.fill("#password", "Password1!")
        page.click("button[type='submit']")
        expect(page).to_have_url(f"{base_url}/dashboard", timeout=6000)
