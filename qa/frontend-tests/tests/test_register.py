from playwright.sync_api import Page, expect


class TestRegisterPage:
    def test_heading_and_subtitle_render(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        expect(page.locator("h1")).to_have_text("Create your account")
        expect(
            page.locator("text=Request access to the pipeline operations console.")
        ).to_be_visible()

    def test_insightflow_logo_visible(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        expect(page.locator("text=InsightFlow").first).to_be_visible()

    def test_all_four_fields_present(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        expect(page.locator("#name")).to_be_visible()
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator("#confirmPassword")).to_be_visible()

    def test_password_hint_visible(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        expect(
            page.locator("text=Use 8+ chars with mixed case, a number or symbol.")
        ).to_be_visible()

    def test_sign_in_link_goes_to_login(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.click("text=Sign in")
        expect(page).to_have_url(f"{base_url}/login")

    def test_single_word_name_shows_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.fill("#name", "Amelia")
        page.fill("#email", "amelia@insightflow.io")
        page.fill("#password", "Password1!")
        page.fill("#confirmPassword", "Password1!")
        page.click("button[type='submit']")
        expect(page.locator("text=Enter your full name.")).to_be_visible()

    def test_invalid_email_shows_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.fill("#name", "Amelia Rivera")
        page.fill("#email", "not-an-email")
        page.fill("#password", "Password1!")
        page.fill("#confirmPassword", "Password1!")
        page.click("button[type='submit']")
        expect(page.locator("text=Enter a valid email address.")).to_be_visible()

    def test_weak_password_shows_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.fill("#name", "Amelia Rivera")
        page.fill("#email", "amelia@insightflow.io")
        page.fill("#password", "weak")
        page.fill("#confirmPassword", "weak")
        page.click("button[type='submit']")
        expect(
            page.locator("text=Password is too weak (8+ chars, mix it up).")
        ).to_be_visible()

    def test_mismatched_passwords_show_error(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.fill("#name", "Amelia Rivera")
        page.fill("#email", "amelia@insightflow.io")
        page.fill("#password", "Password1!")
        page.fill("#confirmPassword", "Different1!")
        page.click("button[type='submit']")
        expect(page.locator("text=Passwords don't match.")).to_be_visible()

    def test_password_fields_masked_by_default(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        expect(page.locator("#password")).to_have_attribute("type", "password")
        expect(page.locator("#confirmPassword")).to_have_attribute("type", "password")

    def test_password_show_hide_toggle(self, page: Page, base_url: str):
        page.goto(f"{base_url}/register")
        page.fill("#password", "Password1!")
        page.locator("button[aria-label='Show password']").first.click()
        expect(page.locator("#password")).to_have_attribute("type", "text")

    def test_successful_registration_redirects_to_dashboard(
        self, page: Page, base_url: str
    ):
        page.goto(f"{base_url}/register")
        page.fill("#name", "Amelia Rivera")
        page.fill("#email", "amelia@insightflow.io")
        page.fill("#password", "Password1!")
        page.fill("#confirmPassword", "Password1!")
        page.click("button[type='submit']")
        expect(page).to_have_url(f"{base_url}/dashboard", timeout=6000)
