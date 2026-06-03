from playwright.sync_api import Page, expect


class TestSidebar:
    def test_insightflow_brand_visible(self, auth_page: Page):
        expect(auth_page.locator("aside").locator("text=InsightFlow")).to_be_visible()

    def test_operations_section_label_visible(self, auth_page: Page):
        expect(auth_page.locator("text=OPERATIONS")).to_be_visible()

    def test_analytics_section_label_visible(self, auth_page: Page):
        expect(auth_page.locator("text=ANALYTICS")).to_be_visible()

    def test_all_nav_items_present(self, auth_page: Page):
        sidebar = auth_page.locator("aside")
        expect(sidebar.locator("text=Dashboard")).to_be_visible()
        expect(sidebar.locator("text=New upload")).to_be_visible()
        expect(sidebar.locator("text=Ingestion history")).to_be_visible()
        expect(sidebar.locator("text=Metabase")).to_be_visible()

    def test_dashboard_link_navigates(self, auth_page: Page, base_url: str):
        auth_page.goto(f"{base_url}/uploads/new")
        auth_page.locator("aside").locator("text=Dashboard").click()
        expect(auth_page).to_have_url(f"{base_url}/dashboard")

    def test_new_upload_link_navigates(self, auth_page: Page, base_url: str):
        auth_page.locator("aside").get_by_role(
            "link", name="New upload", exact=True
        ).click()
        expect(auth_page).to_have_url(f"{base_url}/uploads/new")

    def test_ingestion_history_link_navigates(self, auth_page: Page, base_url: str):
        auth_page.locator("aside").get_by_role("link", name="Ingestion history").click()
        expect(auth_page).to_have_url(f"{base_url}/uploads/history")

    def test_active_link_has_aria_current(self, auth_page: Page):
        expect(auth_page.locator("nav a[aria-current='page']")).to_contain_text(
            "Dashboard"
        )

    def test_user_name_visible_in_sidebar(self, auth_page: Page):
        expect(auth_page.locator("aside")).to_contain_text("Rivera")

    def test_ingestion_history_badge_visible(self, auth_page: Page):
        expect(auth_page.locator("text=64")).to_be_visible()
