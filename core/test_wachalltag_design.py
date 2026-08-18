from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Membership, Station
from core.wachalltag_models import Defect


class WachalltagCursorDesignContractTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Design-Wache",
            slug="design-wache",
            checklists_enabled=True,
        )
        self.user = User.objects.create_user(
            username="design-user",
            password="test-password",
        )
        Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.ADMIN,
        )
        self.defect = Defect.objects.create(
            station=self.station,
            title="Defekte Hallenbeleuchtung",
            created_by=self.user,
        )
        self.client.force_login(self.user)

    def assert_cursor_module_shell(self, response, back_url):
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<a class="back-link" href="{back_url}">',
            html=False,
        )
        self.assertContains(
            response,
            f'href="{reverse("more")}" aria-current="page"',
            html=False,
        )

    def test_module_pages_keep_cursor_back_navigation_and_active_more_tab(self):
        pages = (
            (reverse("defects_web"), reverse("more")),
            (reverse("defect_create_web"), reverse("defects_web")),
            (
                reverse("defect_detail_web", args=[self.defect.pk]),
                reverse("defects_web"),
            ),
            (reverse("assets_inventory_web"), reverse("more")),
            (reverse("checklist_schedules_web"), reverse("checklists")),
            (reverse("wachalltag_reports_web"), reverse("more")),
        )

        for page_url, back_url in pages:
            with self.subTest(page_url=page_url):
                self.assert_cursor_module_shell(self.client.get(page_url), back_url)

    def test_report_uses_existing_cursor_status_components(self):
        response = self.client.get(reverse("wachalltag_reports_web"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="status-summary"', html=False)
        self.assertContains(response, 'class="status-pill', count=5, html=False)
        self.assertNotContains(response, "dashboard-grid")
        self.assertNotContains(response, "metric-card")
