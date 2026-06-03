from playwright.sync_api import Page, expect


class TestForgotPasswordPage:
    def test_heading_and_subtitle_render(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        expect(page.locator("h1")).to_have_text("Reset your password")
        expect(
            page.locator("text=Enter your email and we'll send you a reset link.")
        ).to_be_visible()

    def test_insightflow_logo_visible(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        expect(page.locator("text=InsightFlow").first).to_be_visible()

    def test_email_field_and_submit_button_present(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_have_text("Send reset link")

    def test_back_to_sign_in_link_goes_to_login(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        page.click("text=Back to sign in")
        expect(page).to_have_url(f"{base_url}/login")

    def test_empty_email_shows_validation_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        page.click("button[type='submit']")
        expect(page.locator("text=Enter a valid email address.")).to_be_visible()

    def test_invalid_email_shows_validation_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        page.fill("#email", "not-an-email")
        page.click("button[type='submit']")
        expect(page.locator("text=Enter a valid email address.")).to_be_visible()

    def test_valid_email_shows_success_heading(self, page: Page, base_url: str):
        page.goto(f"{base_url}/forgot-password")
        page.fill("#email", "user@insightflow.io")
        page.click("button[type='submit']")
        expect(page.locator("h2")).to_have_text("Check your inbox")

    def test_success_state_displays_submitted_email(
        self, page: Page, base_url: str
    ):
        page.goto(f"{base_url}/forgot-password")
        page.fill("#email", "user@insightflow.io")
        page.click("button[type='submit']")
        expect(page.locator("text=user@insightflow.io")).to_be_visible()

    def test_try_another_address_returns_to_form(
        self, page: Page, base_url: str
    ):
        page.goto(f"{base_url}/forgot-password")
        page.fill("#email", "user@insightflow.io")
        page.click("button[type='submit']")
        page.click("text=try another address")
        expect(page.locator("h1")).to_have_text("Reset your password")
        expect(page.locator("#email")).to_be_visible()
