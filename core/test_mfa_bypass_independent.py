"""Independent regression checks for the password-login -> MFA-setup bypass."""
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Membership, Station, User


@override_settings(
    MFA_ENABLED=True,
    MFA_REQUIRED=True,
    DEMO_MODE=False,
    DEMO_PUBLIC_MODE=False,
)
class IndependentMFAGateTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Independent MFA test station")
        self.user = User.objects.create_user(
            "independent_mfa_user", password="test-only-not-a-real-credential"
        )
        Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.MEMBER,
            is_active=True,
        )

    def test_password_login_does_not_allow_direct_dashboard_bypass(self):
        response = self.client.post(
            "/anmelden/",
            {"username": self.user.username, "password": "test-only-not-a-real-credential"},
        )
        self.assertRedirects(response, reverse("mfa_setup"), fetch_redirect_response=False)
        # The password step creates a session. The global gate must still block it.
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("mfa_setup"), fetch_redirect_response=False)

    def test_unenrolled_session_cannot_read_or_write_business_routes(self):
        self.client.force_login(self.user)
        for path in (
            "/uebersicht/", "/uebergaben/", "/uebergaben/neu/",
            "/kalender/", "/kaffeekasse/", "/aufgaben/", "/konto/",
        ):
            for method in ("get", "post"):
                with self.subTest(path=path, method=method):
                    response = getattr(self.client, method)(path)
                    self.assertRedirects(
                        response, reverse("mfa_setup"), fetch_redirect_response=False
                    )

    @override_settings(MFA_REQUIRED=False)
    def test_optional_mfa_preserves_dashboard_access(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    @override_settings(MFA_ENABLED=False)
    def test_disabled_mfa_preserves_dashboard_access(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    @override_settings(DEMO_PUBLIC_MODE=True)
    def test_public_demo_exception_preserves_dashboard_access(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
