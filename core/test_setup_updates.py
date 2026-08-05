import io
import json
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from .models import DismissedNotice, Membership, Station, UpdateRequest
from .notice_views import INSTALL_NOTICE_KEY
from .update_service import (
    ReleaseInfo,
    UpdateCheckError,
    is_newer_version,
    normalize_version,
)

SETUP_SETTINGS = {
    "SETUP_WIZARD_ENABLED": True,
    "SETUP_TOKEN": "s" * 64,
    "MFA_ENABLED": True,
}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DockerWorkflowRegressionTests(SimpleTestCase):
    def test_install_and_update_wait_for_compose_healthchecks(self):
        install_script = (PROJECT_ROOT / "scripts" / "install.sh").read_text()
        update_script = (PROJECT_ROOT / "scripts" / "update.sh").read_text()
        self.assertIn("docker compose up -d --wait --wait-timeout 180", install_script)
        self.assertIn("--force-recreate --wait --wait-timeout 90", update_script)

    def test_docker_build_does_not_upgrade_an_unlocked_pip(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
        self.assertNotIn("pip install --upgrade pip", dockerfile)
        self.assertIn("pip install --require-hashes -r requirements.lock", dockerfile)


@override_settings(**SETUP_SETTINGS)
class InitialSetupTests(TestCase):
    def test_fresh_installation_redirects_to_setup(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/einrichtung/", fetch_redirect_response=False)

    def test_setup_requires_matching_token(self):
        response = self.client.post(
            "/einrichtung/",
            {
                "action": "authorize",
                "setup_token": "wrong",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Einrichtungs-Code ist ungültig")
        self.assertNotIn("rwsth_setup_authorized", self.client.session)

    def test_token_in_url_is_removed_before_form_is_shown(self):
        response = self.client.get(f"/einrichtung/?token={'s' * 64}")
        self.assertRedirects(response, "/einrichtung/", fetch_redirect_response=False)
        response = self.client.get("/einrichtung/")
        self.assertContains(response, "Wache und Master-Admin")
        self.assertNotContains(response, "s" * 64)

    def test_setup_creates_first_station_admin_and_audit(self):
        self.client.get(f"/einrichtung/?token={'s' * 64}")
        response = self.client.post(
            "/einrichtung/",
            {
                "action": "configure",
                "station_name": "Rettungswache Nord",
                "username": "master-admin",
                "first_name": "Mara",
                "last_name": "Muster",
                "email": "mara@example.org",
                "password1": "Sicheres-Startpasswort-2026!",
                "password2": "Sicheres-Startpasswort-2026!",
                "calendar_enabled": "on",
                "tasks_enabled": "on",
                "chat_enabled": "on",
                "coffee_enabled": "on",
                "birthdays_enabled": "on",
                "product_boundary": "on",
                "operator_responsibility": "on",
            },
        )
        self.assertRedirects(
            response, "/einrichtung/abgeschlossen/", fetch_redirect_response=False
        )
        membership = Membership.objects.select_related("station", "user").get()
        self.assertEqual(membership.role, Membership.Role.ADMIN)
        self.assertEqual(membership.station.name, "Rettungswache Nord")
        self.assertTrue(membership.user.check_password("Sicheres-Startpasswort-2026!"))
        self.assertTrue(
            membership.station.auditevent_set.filter(
                action="installation.setup_completed"
            ).exists()
        )

    @override_settings(SETUP_TOKEN="too-short")
    def test_insecure_setup_token_cannot_authorize(self):
        response = self.client.get("/einrichtung/")
        self.assertContains(response, "Einrichtungs-Code fehlt")


class _AdminBase(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Testwache", slug="testwache")
        self.user = User.objects.create_user("admin", password="test-password")
        self.membership = Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.ADMIN,
        )
        self.client.force_login(self.user)


class NoticeDismissalTests(_AdminBase):
    def test_install_notice_dismissal_is_persisted_for_user(self):
        response = self.client.get("/mehr/")
        self.assertContains(response, "data-install-banner")
        response = self.client.post(
            "/hinweise/app-installation/ausblenden/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.json(), {"ok": True})
        self.assertTrue(
            DismissedNotice.objects.filter(
                user=self.user, notice_key=INSTALL_NOTICE_KEY
            ).exists()
        )
        response = self.client.get("/mehr/")
        self.assertNotContains(response, "data-install-banner")


class UpdateViewTests(_AdminBase):
    release = ReleaseInfo(
        version="0.16.0",
        tag="v0.16.0",
        url="https://github.com/Darkspike1988/Rettungswache-Wachbuch/releases/tag/v0.16.0",
        published_at="2026-08-04T12:00:00Z",
        notes="Release notes",
    )

    @patch("core.update_views.fetch_latest_release", return_value=release)
    def test_admin_can_check_and_request_update(self, _fetch):
        response = self.client.post("/system/updates/", {"action": "check"})
        self.assertContains(response, "Neuestes Release: 0.16.0")
        response = self.client.post("/system/updates/", {"action": "request"})
        self.assertRedirects(response, "/system/updates/")
        update = UpdateRequest.objects.get()
        self.assertEqual(update.status, UpdateRequest.Status.PENDING)
        self.assertEqual(update.target_version, "0.16.0")

    @patch(
        "core.update_views.fetch_latest_release",
        side_effect=UpdateCheckError("offline"),
    )
    def test_update_check_failure_is_a_safe_message(self, _fetch):
        response = self.client.post("/system/updates/", {"action": "check"})
        self.assertContains(response, "offline")
        self.assertEqual(UpdateRequest.objects.count(), 0)

    def test_non_admin_cannot_open_updates(self):
        self.membership.role = Membership.Role.MEMBER
        self.membership.save(update_fields=["role"])
        response = self.client.get("/system/updates/")
        self.assertEqual(response.status_code, 403)

    def test_invalid_cancel_request_id_returns_not_found(self):
        response = self.client.post(
            "/system/updates/",
            {"action": "cancel", "request_id": "invalid"},
        )
        self.assertEqual(response.status_code, 404)


class UpdateCommandTests(_AdminBase):
    def test_claim_and_finish_update_request(self):
        update = UpdateRequest.objects.create(
            requested_by=self.user,
            station=self.station,
            current_version="0.15.0",
            target_version="0.16.0",
            release_url="https://github.com/Darkspike1988/Rettungswache-Wachbuch/releases/tag/v0.16.0",
        )
        stdout = io.StringIO()
        call_command("manage_update_requests", "--claim", stdout=stdout)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["request"]["id"], update.pk)
        update.refresh_from_db()
        self.assertEqual(update.status, UpdateRequest.Status.RUNNING)

        call_command(
            "manage_update_requests",
            "--finish",
            str(update.pk),
            "--status",
            "succeeded",
            "--message",
            "ok",
            stdout=io.StringIO(),
        )
        update.refresh_from_db()
        self.assertEqual(update.status, UpdateRequest.Status.SUCCEEDED)
        self.assertEqual(update.result_message, "ok")


class VersionComparisonTests(TestCase):
    def test_semver_normalization_and_order(self):
        self.assertEqual(normalize_version("v1.2.3"), "1.2.3")
        self.assertTrue(is_newer_version("1.2.4", "1.2.3"))
        self.assertTrue(is_newer_version("1.2.3", "1.2.3-rc.1"))
        self.assertFalse(is_newer_version("1.2.3", "1.2.3"))

    def test_invalid_semver_is_rejected(self):
        with self.assertRaises(UpdateCheckError):
            normalize_version("latest")
