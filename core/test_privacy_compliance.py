import os
from unittest.mock import patch

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from .checks import privacy_security_deployment_checks
from .models import Station
from .privacy_models import DataProtectionOfficer


class DataProtectionOfficerTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Wache Nord", slug="wache-nord")

    def test_model_is_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(DataProtectionOfficer))

    def test_only_one_active_primary_contact_per_station(self):
        DataProtectionOfficer.objects.create(
            station=self.station,
            display_name="Datenschutz Hauptkontakt",
            email="datenschutz@example.invalid",
            is_primary=True,
        )
        second = DataProtectionOfficer(
            station=self.station,
            display_name="Zweiter Hauptkontakt",
            email="datenschutz2@example.invalid",
            is_primary=True,
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_inactive_contact_cannot_be_marked_public(self):
        contact = DataProtectionOfficer(
            station=self.station,
            display_name="Inaktiv",
            email="inactive@example.invalid",
            is_active=False,
            publish_in_privacy_notice=True,
        )
        with self.assertRaises(ValidationError):
            contact.full_clean()

    def test_privacy_page_exposes_only_explicitly_public_active_contact(self):
        DataProtectionOfficer.objects.create(
            station=self.station,
            display_name="Öffentlicher Datenschutzkontakt",
            organization="Datenschutzstelle Beispiel",
            email="privacy@example.invalid",
            phone="+49 123 456789",
            postal_address="Musterweg 1\n12345 Beispielstadt",
            is_primary=True,
            internal_notes="DARF-NIEMALS-OEFFENTLICH-SEIN",
        )
        DataProtectionOfficer.objects.create(
            station=self.station,
            display_name="Interner Datenschutzkontakt",
            email="internal@example.invalid",
            publish_in_privacy_notice=False,
        )

        response = self.client.get("/datenschutz/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Öffentlicher Datenschutzkontakt")
        self.assertContains(response, "privacy@example.invalid")
        self.assertContains(response, "Wache Nord")
        self.assertNotContains(response, "Interner Datenschutzkontakt")
        self.assertNotContains(response, "internal@example.invalid")
        self.assertNotContains(response, "DARF-NIEMALS-OEFFENTLICH-SEIN")

    def test_inactive_station_contact_is_not_public(self):
        self.station.is_active = False
        self.station.save(update_fields=["is_active"])
        DataProtectionOfficer.objects.create(
            station=self.station,
            display_name="Nicht veröffentlichen",
            email="hidden@example.invalid",
        )
        response = self.client.get("/datenschutz/")
        self.assertNotContains(response, "hidden@example.invalid")


class PrivacyDeploymentChecksTests(TestCase):
    @override_settings(MFA_REQUIRED=False, SECURE_COOKIES=False, RETENTION_AUDIT_DAYS=0)
    def test_deploy_checks_flag_missing_hardening(self):
        with patch.dict(os.environ, {"CRYPTO_MASTER_KEY": ""}, clear=False):
            warnings = privacy_security_deployment_checks(None)
        ids = {warning.id for warning in warnings}
        self.assertEqual(
            ids,
            {"wachbuch.W101", "wachbuch.W102", "wachbuch.W103", "wachbuch.W104"},
        )

    @override_settings(MFA_REQUIRED=True, SECURE_COOKIES=True, RETENTION_AUDIT_DAYS=90)
    def test_deploy_checks_pass_documented_production_profile(self):
        with patch.dict(
            os.environ,
            {"CRYPTO_MASTER_KEY": "11" * 32},
            clear=False,
        ):
            warnings = privacy_security_deployment_checks(None)
        self.assertEqual(warnings, [])
