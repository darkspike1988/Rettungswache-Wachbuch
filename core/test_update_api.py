from datetime import date

from django.urls import reverse

from .models import AppVersion
from .tests import PilotTestCase


class CheckUpdateTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        AppVersion.objects.all().delete()

    def _url(self, current="0.1.0", platform="android"):
        return reverse("api_v1_check_update") + f"?current_version={current}&platform={platform}"

    def test_no_version_configured_reports_no_update(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["has_update"])

    def test_newer_version_reports_update(self):
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.2.0",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.1.0"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["has_update"])
        self.assertEqual(payload["latest_version"], "0.2.0")
        self.assertFalse(payload["force_update"])

    def test_matching_version_reports_no_update(self):
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.1.0",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.1.0"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_update"])

    def test_newer_client_is_not_asked_to_downgrade(self):
        # Regression (release-109): has_update used string inequality, so a
        # client NEWER than the published latest was told to "update"
        # (i.e. downgrade). has_update must follow version order, not text.
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.2.0",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.3.0"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["has_update"])
        self.assertEqual(payload["latest_version"], "0.2.0")

    def test_numeric_version_ordering_not_lexicographic(self):
        # "0.10.0" is newer than "0.9.0" even though it sorts lower as text.
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.9.0",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.10.0"))
        self.assertFalse(response.json()["has_update"])

    def test_release_date_tie_is_deterministic(self):
        # Two active versions on the same release_date must resolve to a single
        # deterministic "latest" instead of relying on undefined row order.
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.2.0",
            version_code=2,
            release_date=date.today(),
        )
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.3.0",
            version_code=3,
            release_date=date.today(),
        )
        first = self.client.get(self._url(current="0.1.0")).json()["latest_version"]
        second = self.client.get(self._url(current="0.1.0")).json()["latest_version"]
        self.assertEqual(first, second)
        # Documented rule: highest id wins the tie (most recently created row).
        self.assertEqual(first, "0.3.0")

    def test_min_required_version_forces_update(self):
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.3.0",
            min_required_version="0.2.0",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.1.0"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_update"])
        self.assertTrue(payload["force_update"])

    def test_platforms_are_isolated(self):
        AppVersion.objects.create(
            platform=AppVersion.Platform.IOS,
            version="9.9.9",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.1.0", platform="android"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_update"])

    def test_download_url_is_passed_through(self):
        AppVersion.objects.create(
            platform=AppVersion.Platform.ANDROID,
            version="0.2.0",
            download_url="https://example.org/app.apk",
            release_date=date.today(),
        )
        response = self.client.get(self._url(current="0.1.0"))
        self.assertEqual(response.json()["download_url"], "https://example.org/app.apk")
