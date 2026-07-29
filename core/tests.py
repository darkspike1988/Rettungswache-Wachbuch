import json
import re
import time
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pyotp

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import WachbuchUserCreationForm
from .feed_sync import fetch_source, sync_closure_csv, sync_rss, sync_waste_ics
from .geocoding import GeocodingError, lookup_district
from .twofactor import issue_recovery_codes
from .models import (
    AuditEvent,
    BirthdayPreference,
    CoffeeEntry,
    DailyTeamNote,
    FeedItem,
    FeedSource,
    HandoverEntry,
    HandoverRevision,
    Membership,
    Station,
    TotpDevice,
)


class PilotTestCase(TestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Testwache",
            slug="testwache",
            feeds_enabled=True,
            onboarded=True,
        )
        self.user = User.objects.create_user("member@example.org", first_name="Mara")
        self.membership = Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        self.client.force_login(self.user)


class SetupWizardTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Neue Wache", slug="neue-wache")
        self.admin = User.objects.create_user("admin@example.org", first_name="Nora")
        self.membership = Membership.objects.create(
            user=self.admin, station=self.station, role=Membership.Role.ADMIN,
        )
        self.member = User.objects.create_user("member@example.org", first_name="Mo")
        Membership.objects.create(
            user=self.member, station=self.station, role=Membership.Role.MEMBER,
        )

    def test_new_admin_is_redirected_to_wizard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("setup_wizard"))

    def test_member_is_not_redirected_to_wizard(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_access_wizard(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("setup_wizard"))
        self.assertEqual(response.status_code, 403)

    def test_wizard_walkthrough_completes_and_unlocks_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("setup_wizard"), {
            "name": "Rettungswache Demo", "location": "Musterstadt",
        })
        self.assertRedirects(response, reverse("setup_wizard", args=["modules"]))
        response = self.client.post(reverse("setup_wizard", args=["modules"]), {
            "calendar_enabled": "on", "coffee_enabled": "on",
        })
        self.assertRedirects(response, reverse("setup_wizard", args=["done"]))
        response = self.client.post(reverse("setup_wizard", args=["done"]))
        self.assertRedirects(response, reverse("dashboard"))

        self.station.refresh_from_db()
        self.assertEqual(self.station.name, "Rettungswache Demo")
        self.assertTrue(self.station.calendar_enabled)
        self.assertFalse(self.station.birthdays_enabled)
        self.assertTrue(self.station.onboarded)
        self.assertTrue(AuditEvent.objects.filter(action="station.onboarding_completed").exists())
        self.assertTrue(AuditEvent.objects.filter(action="station.onboarding_step_saved").exists())

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_skip_marks_onboarded_without_changes(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("setup_wizard"), {"skip_all": "1"})
        self.assertRedirects(response, reverse("dashboard"))
        self.station.refresh_from_db()
        self.assertTrue(self.station.onboarded)
        self.assertEqual(self.station.name, "Neue Wache")
        self.assertTrue(AuditEvent.objects.filter(action="station.onboarding_skipped").exists())


class MultiStationTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.second = Station.objects.create(
            name="Zweitwache", slug="zweitwache", onboarded=True,
        )
        self.second_membership = Membership.objects.create(
            user=self.user, station=self.second, role=Membership.Role.SHIFT_LEAD,
        )

    def test_a_person_may_belong_to_several_stations(self):
        self.assertEqual(self.user.station_memberships.filter(is_active=True).count(), 2)

    def test_switching_changes_the_visible_station(self):
        HandoverEntry.objects.create(
            station=self.station, category=HandoverEntry.Category.TASK,
            title="Nur Testwache", details="x", author=self.user,
        )
        HandoverEntry.objects.create(
            station=self.second, category=HandoverEntry.Category.TASK,
            title="Nur Zweitwache", details="x", author=self.user,
        )
        response = self.client.get(reverse("handover_list"))
        self.assertContains(response, "Nur Testwache")
        self.assertNotContains(response, "Nur Zweitwache")

        switch = self.client.post(reverse("switch_station"), {"station": self.second.pk})
        self.assertRedirects(switch, reverse("dashboard"))

        response = self.client.get(reverse("handover_list"))
        self.assertContains(response, "Nur Zweitwache")
        self.assertNotContains(response, "Nur Testwache")

    def test_role_follows_the_selected_station(self):
        # Mitglied auf der Testwache, Schichtleitung auf der Zweitwache.
        handover = HandoverEntry.objects.create(
            station=self.second, category=HandoverEntry.Category.TASK,
            title="Status aendern", details="x", author=self.user,
        )
        self.client.post(reverse("switch_station"), {"station": self.second.pk})
        response = self.client.post(reverse("handover_status", args=[handover.pk]), {
            "status": HandoverEntry.Status.DONE,
        })
        self.assertEqual(response.status_code, 302)
        handover.refresh_from_db()
        self.assertEqual(handover.status, HandoverEntry.Status.DONE)

    def test_cannot_switch_to_a_station_without_membership(self):
        foreign = Station.objects.create(name="Fremd", slug="fremd-switch")
        response = self.client.post(reverse("switch_station"), {"station": foreign.pk})
        self.assertEqual(response.status_code, 403)

    def test_revoked_access_falls_back_instead_of_breaking(self):
        self.client.post(reverse("switch_station"), {"station": self.second.pk})
        self.second_membership.is_active = False
        self.second_membership.save(update_fields=["is_active"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Testwache")


class TeamPrivacyTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        self.other_station = Station.objects.create(name="Andere", slug="andere-team")
        self.foreign_user = User.objects.create_user(
            "fremd@example.org", email="fremd@example.org", first_name="Fremd",
        )
        Membership.objects.create(
            user=self.foreign_user, station=self.other_station, role=Membership.Role.MEMBER,
        )

    def test_form_does_not_list_accounts_of_other_stations(self):
        response = self.client.get(reverse("team_create"))
        self.assertNotContains(response, "fremd@example.org")

    def test_pending_count_ignores_members_of_other_stations(self):
        response = self.client.get(reverse("team"))
        self.assertEqual(response.context["pending_count"], 0)

        User.objects.create_user("wartend@example.org", email="wartend@example.org")
        response = self.client.get(reverse("team"))
        self.assertEqual(response.context["pending_count"], 1)

    def test_known_address_can_be_added_as_a_second_station(self):
        response = self.client.post(reverse("team_create"), {
            "email": "fremd@example.org", "role": Membership.Role.MEMBER,
        })
        self.assertRedirects(response, reverse("team"))
        self.assertTrue(
            Membership.objects.filter(user=self.foreign_user, station=self.station).exists()
        )

    def test_unknown_address_is_rejected_without_creating_anything(self):
        response = self.client.post(reverse("team_create"), {
            "email": "gibtsnicht@example.org", "role": Membership.Role.MEMBER,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "kein aktives Konto")

    def test_duplicate_assignment_is_rejected(self):
        response = self.client.post(reverse("team_create"), {
            "email": self.user.username, "role": Membership.Role.MEMBER,
        })
        self.assertContains(response, "bereits zugeordnet")


class SecurityAndAccessTests(PilotTestCase):
    def test_anonymous_header_shows_login_link(self):
        self.client.logout()
        response = self.client.get(reverse("access"))
        self.assertContains(response, f'href="{reverse("login")}"')

    def test_health_endpoint_and_security_headers(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_user_without_membership_waits_for_approval(self):
        outsider = User.objects.create_user("outside@example.org")
        self.client.force_login(outsider)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("access"))

    def test_auditor_cannot_read_station_content(self):
        self.membership.role = Membership.Role.AUDITOR
        self.membership.save(update_fields=["role"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 403)

    @override_settings(
        TRUST_TAILSCALE_HEADERS=True,
        TAILSCALE_ADMIN_LOGIN="pilot-admin@example.org",
    )
    def test_tailscale_header_bootstraps_only_configured_admin(self):
        self.client.logout()
        response = self.client.get(
            reverse("dashboard"),
            HTTP_TAILSCALE_USER_LOGIN="pilot-admin@example.org",
            HTTP_TAILSCALE_USER_NAME="Pilot Admin",
        )
        self.assertEqual(response.status_code, 200)
        admin = User.objects.get(username="pilot-admin@example.org")
        self.assertFalse(admin.is_superuser)
        membership = admin.station_memberships.get()
        self.assertEqual(membership.role, Membership.Role.ADMIN)
        self.assertEqual(membership.station, self.station)
        self.assertEqual(Station.objects.count(), 1)

    @override_settings(TRUST_TAILSCALE_HEADERS=True)
    def test_missing_tailscale_header_ends_existing_session(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("access"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(TRUST_TAILSCALE_HEADERS=True)
    def test_inactive_tailscale_user_is_not_logged_in(self):
        self.client.logout()
        inactive = User.objects.create_user("inactive@example.org", is_active=False)
        response = self.client.get(
            reverse("dashboard"),
            HTTP_TAILSCALE_USER_LOGIN=inactive.username,
        )
        self.assertRedirects(response, reverse("access"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_can_log_out_from_interface(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, reverse("logout"))
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("access"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(AXES_FAILURE_LIMIT=3, AXES_COOLOFF_TIME=1)
    def test_password_login_is_rate_limited(self):
        User.objects.create_user("limited@example.org", password="correct-password")
        self.client.logout()
        for _ in range(3):
            response = self.client.post(
                reverse("login"),
                {"username": "limited@example.org", "password": "wrong-password"},
                REMOTE_ADDR="198.51.100.20",
            )
        self.assertEqual(response.status_code, 429)


class HandoverTests(PilotTestCase):
    def make_handover(self):
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.NORMAL,
            title="Tor pruefen",
            details="Der Endschalter reagiert zeitweise nicht.",
            author=self.user,
        )
        HandoverRevision.objects.create(
            handover=handover,
            version=1,
            snapshot={"status": handover.status},
            changed_by=self.user,
        )
        return handover

    def test_member_creates_versioned_handover_and_audit(self):
        response = self.client.post(reverse("handover_create"), {
            "category": HandoverEntry.Category.MATERIAL,
            "priority": HandoverEntry.Priority.IMPORTANT,
            "title": "Bestand kontrollieren",
            "details": "Versiegeltes Verbrauchsmaterial nachbestellen.",
        })
        handover = HandoverEntry.objects.get(title="Bestand kontrollieren")
        self.assertRedirects(response, reverse("handover_detail", args=[handover.pk]))
        self.assertEqual(handover.revisions.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="handover.created").exists())

    def test_member_cannot_change_status(self):
        handover = self.make_handover()
        response = self.client.post(reverse("handover_status", args=[handover.pk]), {
            "status": HandoverEntry.Status.DONE,
        })
        self.assertEqual(response.status_code, 403)
        handover.refresh_from_db()
        self.assertEqual(handover.status, HandoverEntry.Status.OPEN)

    def test_shift_lead_status_change_creates_revision(self):
        handover = self.make_handover()
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("handover_status", args=[handover.pk]), {
            "status": HandoverEntry.Status.DONE,
        })
        self.assertRedirects(response, reverse("handover_detail", args=[handover.pk]))
        handover.refresh_from_db()
        self.assertEqual(handover.version, 2)
        self.assertIsNotNone(handover.completed_at)
        self.assertEqual(handover.revisions.count(), 2)

    def test_author_edits_own_handover_and_gets_a_revision(self):
        handover = self.make_handover()
        response = self.client.post(reverse("handover_edit", args=[handover.pk]), {
            "category": HandoverEntry.Category.SAFETY,
            "priority": HandoverEntry.Priority.URGENT,
            "title": "Tor pruefen (korrigiert)",
            "details": "Der Endschalter reagiert gar nicht mehr.",
            "for_date": "",
        })
        self.assertRedirects(response, reverse("handover_detail", args=[handover.pk]))
        handover.refresh_from_db()
        self.assertEqual(handover.title, "Tor pruefen (korrigiert)")
        self.assertEqual(handover.priority, HandoverEntry.Priority.URGENT)
        self.assertEqual(handover.version, 2)
        self.assertEqual(handover.revisions.count(), 2)
        self.assertEqual(
            handover.revisions.order_by("-version").first().snapshot["title"],
            "Tor pruefen (korrigiert)",
        )
        self.assertTrue(AuditEvent.objects.filter(action="handover.updated").exists())

    def test_member_cannot_edit_someone_elses_handover(self):
        other = User.objects.create_user("other-author@example.org")
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            title="Fremder Eintrag",
            details="Nicht meiner",
            author=other,
        )
        response = self.client.get(reverse("handover_edit", args=[handover.pk]))
        self.assertEqual(response.status_code, 403)

    def test_shift_lead_may_edit_someone_elses_handover(self):
        other = User.objects.create_user("other-author2@example.org")
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            title="Fremder Eintrag",
            details="Nicht meiner",
            author=other,
        )
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        self.assertEqual(
            self.client.get(reverse("handover_edit", args=[handover.pk])).status_code, 200
        )

    def test_edit_of_foreign_station_handover_is_not_found(self):
        other_station = Station.objects.create(name="Fremd", slug="fremd")
        handover = HandoverEntry.objects.create(
            station=other_station,
            category=HandoverEntry.Category.TASK,
            title="Stationsfremd",
            details="x",
            author=self.user,
        )
        response = self.client.get(reverse("handover_edit", args=[handover.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cross_station_object_is_hidden(self):
        other = Station.objects.create(name="Andere", slug="andere")
        handover = HandoverEntry.objects.create(
            station=other,
            category=HandoverEntry.Category.TASK,
            title="Nicht sichtbar",
            details="Stationsfremd",
            author=self.user,
        )
        response = self.client.get(reverse("handover_detail", args=[handover.pk]))
        self.assertEqual(response.status_code, 404)


class WeeklyProtocolTests(PilotTestCase):
    def test_week_view_groups_day_and_general_entries(self):
        today = timezone.localdate()
        HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            title="Fahrzeugcheck",
            details="Taeglicher Check der Ausruestung.",
            author=self.user,
            for_date=today,
        )
        HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            title="Allgemeiner Hinweis",
            details="Ohne Tagesbezug.",
            author=self.user,
        )
        response = self.client.get(reverse("handover_week"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fahrzeugcheck")
        self.assertContains(response, "Allgemeiner Hinweis")

    def test_week_can_be_exported_as_pdf(self):
        today = timezone.localdate()
        HandoverEntry.objects.create(
            station=self.station, category=HandoverEntry.Category.TASK,
            title="Fahrzeugcheck", details="x", author=self.user, for_date=today,
        )
        DailyTeamNote.objects.create(
            station=self.station, date=today, note="Dotzki/Huber", updated_by=self.user,
        )
        year, week, _ = today.isocalendar()
        response = self.client.get(
            reverse("handover_week_pdf"), {"jahr": year, "kw": week}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("wochenprotokoll-kw", response["Content-Disposition"])
        payload = b"".join(response.streaming_content)
        self.assertTrue(payload.startswith(b"%PDF-"))
        self.assertGreater(len(payload), 1000)
        self.assertTrue(AuditEvent.objects.filter(action="handover.week_exported").exists())

    def test_pdf_export_of_a_foreign_station_is_not_possible(self):
        other = Station.objects.create(name="Fremd", slug="fremd-pdf")
        HandoverEntry.objects.create(
            station=other, category=HandoverEntry.Category.TASK,
            title="Geheimer Fremdeintrag", details="x", author=self.user,
            for_date=timezone.localdate(),
        )
        response = self.client.get(reverse("handover_week_pdf"))
        payload = b"".join(response.streaming_content)
        self.assertNotIn(b"Geheimer Fremdeintrag", payload)

    def test_shift_lead_sets_daily_team_note(self):
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        today = timezone.localdate()
        response = self.client.post(
            reverse("daily_team_update", args=[today.isoformat()]),
            {"note": "Dotzki/Huber"},
        )
        year, week, _ = today.isocalendar()
        self.assertRedirects(response, f"{reverse('handover_week')}?jahr={year}&kw={week}")
        note = DailyTeamNote.objects.get(station=self.station, date=today)
        self.assertEqual(note.note, "Dotzki/Huber")
        self.assertTrue(AuditEvent.objects.filter(action="handover.team_set").exists())

    def test_member_cannot_set_daily_team_note(self):
        today = timezone.localdate()
        response = self.client.post(
            reverse("daily_team_update", args=[today.isoformat()]),
            {"note": "Nicht erlaubt"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DailyTeamNote.objects.filter(station=self.station).exists())

    def test_station_settings_location_appears_in_header(self):
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("station_settings"), {
            "name": "Rettungswache Steinhagen",
            "location": "Steinhagen",
        })
        self.assertRedirects(response, reverse("station_settings"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.location, "Steinhagen")
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, "Rettungswache Steinhagen")
        self.assertContains(dashboard, "Steinhagen")


class MinimalInterfaceTests(PilotTestCase):
    def create_handover(self, title, priority, status=HandoverEntry.Status.OPEN):
        return HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            priority=priority,
            status=status,
            title=title,
            details="Testinhalt",
            author=self.user,
        )

    def test_dashboard_only_contains_core_shift_information(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Für die nächste Schicht")
        self.assertContains(response, "Nächste Termine")
        self.assertNotContains(response, "Aktuelle Meldungen")
        self.assertNotContains(response, "Datenraum")
        self.assertNotContains(response, "Geburtstage")

    def test_active_handovers_are_prioritized_and_archive_is_separate(self):
        normal = self.create_handover("Normal", HandoverEntry.Priority.NORMAL)
        urgent = self.create_handover("Dringend", HandoverEntry.Priority.URGENT)
        done = self.create_handover(
            "Erledigt",
            HandoverEntry.Priority.URGENT,
            HandoverEntry.Status.DONE,
        )
        response = self.client.get(reverse("handover_list"))
        items = list(response.context["page_obj"].object_list)
        self.assertEqual([item.pk for item in items], [urgent.pk, normal.pk])
        self.assertNotIn(done.pk, [item.pk for item in items])

        archive = self.client.get(reverse("handover_list"), {"ansicht": "archiv"})
        self.assertEqual([item.pk for item in archive.context["page_obj"].object_list], [done.pk])

    def test_write_forms_use_dedicated_pages(self):
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        calendar = self.client.get(reverse("calendar"))
        create = self.client.get(reverse("calendar_create"))
        self.assertNotContains(calendar, '<form method="post" class="form-card"', html=False)
        self.assertContains(calendar, "Termin anlegen")
        self.assertContains(create, "<form", html=False)

    def test_more_page_holds_secondary_modules(self):
        response = self.client.get(reverse("more"))
        self.assertContains(response, "Geburtstage")
        self.assertContains(response, "Kaffeekasse")
        self.assertContains(response, "Meldungen, Verkehr &amp; Müllabfuhr", html=True)

    def test_coffee_ledger_is_a_semantic_table(self):
        response = self.client.get(reverse("coffee"))
        self.assertContains(response, "<table", html=False)
        self.assertContains(response, "<caption>Kassenbuchungen</caption>", html=True)

    def test_admin_pages_render_with_one_main_heading(self):
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        handover = self.create_handover("Pruefpunkt", HandoverEntry.Priority.IMPORTANT)
        coffee = CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=250,
            reason="Testbuchung",
            created_by=self.user,
        )
        User.objects.create_user("waiting@example.org")
        urls = [
            reverse("dashboard"),
            reverse("handover_list"),
            reverse("handover_create"),
            reverse("handover_detail", args=[handover.pk]),
            reverse("calendar"),
            reverse("calendar_create"),
            reverse("birthdays"),
            reverse("birthday_settings"),
            reverse("coffee"),
            reverse("coffee_create"),
            reverse("coffee_correct", args=[coffee.pk]),
            reverse("feeds"),
            reverse("more"),
            reverse("team"),
            reverse("team_create"),
            reverse("membership_update", args=[self.membership.pk]),
            reverse("station_settings"),
            reverse("audit_log"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.count(b"<h1"), 1)


class BirthdayAndCoffeeTests(PilotTestCase):
    def test_birthday_is_opt_in_and_stores_no_year(self):
        response = self.client.post(reverse("birthday_settings"), {
            "day": 14,
            "month": 6,
            "consent": "on",
        })
        self.assertRedirects(response, reverse("birthdays"))
        preference = BirthdayPreference.objects.get(user=self.user, station=self.station)
        self.assertTrue(preference.is_visible)
        self.assertEqual(preference.day, 14)
        self.assertEqual(preference.month, 6)
        self.assertFalse(hasattr(preference, "year"))

        response = self.client.post(reverse("birthday_settings"), {
            "day": 14,
            "month": 6,
        })
        self.assertRedirects(response, reverse("birthdays"))
        preference.refresh_from_db()
        self.assertFalse(preference.is_visible)
        self.assertIsNone(preference.day)
        self.assertIsNone(preference.month)
        self.assertIsNone(preference.consented_at)
        self.assertIsNotNone(preference.withdrawn_at)

    def test_coffee_entries_are_immutable(self):
        entry = CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=500,
            reason="Einzahlung",
            created_by=self.user,
        )
        entry.reason = "Still geaendert"
        with self.assertRaises(ValidationError):
            entry.save()
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_only_cashier_can_create_coffee_entry(self):
        response = self.client.post(reverse("coffee_create"), {
            "member": self.user.pk,
            "direction": "credit",
            "amount_eur": Decimal("3.50"),
            "reason": "Einzahlung",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CoffeeEntry.objects.count(), 0)

        self.membership.role = Membership.Role.CASHIER
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("coffee_create"), {
            "member": self.user.pk,
            "direction": "credit",
            "amount_eur": Decimal("3.50"),
            "reason": "Einzahlung",
        })
        self.assertRedirects(response, reverse("coffee"))
        self.assertEqual(CoffeeEntry.objects.get().amount_cents, 350)

    def test_correction_requires_same_member_and_exact_counter_amount(self):
        original = CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=500,
            reason="Einzahlung",
            created_by=self.user,
        )
        other = User.objects.create_user("other@example.org")
        with self.assertRaises(ValidationError):
            CoffeeEntry.objects.create(
                station=self.station,
                member=other,
                amount_cents=-400,
                reason="Falsche Korrektur",
                created_by=self.user,
                correction_of=original,
            )
        correction = CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=-500,
            reason="Korrektur",
            created_by=self.user,
            correction_of=original,
        )
        self.assertEqual(correction.amount_cents, -500)

    def test_member_cannot_configure_coffee_payment_options(self):
        response = self.client.post(reverse("coffee_payment_update"), {
            "coffee_paypal_link": "https://paypal.me/hack",
        })
        self.assertEqual(response.status_code, 403)


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            "mara@example.org", email="mara@example.org", password="alt-passwort-123",
        )

    def request_reset(self, address):
        return self.client.post(reverse("password_reset"), {"email": address}, follow=True)

    def test_reset_mail_is_sent_and_new_password_works(self):
        response = self.request_reset("mara@example.org")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"/passwort-neu/[^\s]+/", mail.outbox[0].body).group()

        follow = self.client.get(link, follow=True)
        form_url = follow.redirect_chain[-1][0] if follow.redirect_chain else link
        done = self.client.post(form_url, {
            "new_password1": "ganz-neues-passwort-42",
            "new_password2": "ganz-neues-passwort-42",
        })
        self.assertEqual(done.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ganz-neues-passwort-42"))

    def test_reset_finds_account_when_only_the_username_is_the_address(self):
        User.objects.filter(pk=self.user.pk).update(email="")
        self.request_reset("mara@example.org")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["mara@example.org"])

    def test_unknown_address_reveals_nothing_and_sends_nothing(self):
        response = self.request_reset("niemand@example.org")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(PASSWORD_RESET_MAX_PER_EMAIL=2, PASSWORD_RESET_MAX_PER_IP=99)
    def test_repeated_requests_for_one_address_are_throttled(self):
        for _ in range(2):
            self.request_reset("mara@example.org")
        self.assertEqual(len(mail.outbox), 2)

        response = self.request_reset("mara@example.org")
        # Gleiche Antwort wie im Erfolgsfall, aber keine weitere Mail.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(PASSWORD_RESET_MAX_PER_EMAIL=99, PASSWORD_RESET_MAX_PER_IP=2)
    def test_many_addresses_from_one_client_are_throttled(self):
        for index in range(3):
            User.objects.create_user(
                f"p{index}@example.org", email=f"p{index}@example.org", password="x-123456",
            )
            self.request_reset(f"p{index}@example.org")
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(PASSWORD_RESET_MAX_PER_EMAIL=1, PASSWORD_RESET_MAX_PER_IP=99)
    def test_throttling_one_address_does_not_block_another(self):
        User.objects.create_user(
            "other@example.org", email="other@example.org", password="x-123456",
        )
        self.request_reset("mara@example.org")
        self.request_reset("mara@example.org")
        self.request_reset("other@example.org")
        recipients = [message.to[0] for message in mail.outbox]
        self.assertEqual(recipients, ["mara@example.org", "other@example.org"])

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("password_reset"))

    def test_admin_cannot_create_user_without_email(self):
        form = WachbuchUserCreationForm({
            "username": "ohne@example.org", "password1": "x", "password2": "x",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class AcknowledgementTests(PilotTestCase):
    def make_urgent(self):
        return HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.SAFETY,
            priority=HandoverEntry.Priority.URGENT,
            title="Defekte Absturzsicherung",
            details="Bitte nicht benutzen.",
            author=self.user,
        )

    def test_urgent_entry_can_be_acknowledged_once(self):
        handover = self.make_urgent()
        url = reverse("handover_acknowledge", args=[handover.pk])
        self.assertRedirects(
            self.client.post(url), reverse("handover_detail", args=[handover.pk])
        )
        self.client.post(url)
        self.assertEqual(handover.acknowledgements.count(), 1)
        self.assertEqual(
            AuditEvent.objects.filter(action="handover.acknowledged").count(), 1
        )

    def test_normal_entry_cannot_be_acknowledged(self):
        handover = HandoverEntry.objects.create(
            station=self.station, category=HandoverEntry.Category.TASK,
            title="Normal", details="x", author=self.user,
        )
        response = self.client.post(reverse("handover_acknowledge", args=[handover.pk]))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_lists_unconfirmed_urgent_entries_then_clears(self):
        handover = self.make_urgent()
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Defekte Absturzsicherung")
        self.assertContains(response, "noch nicht von dir best")

        self.client.post(reverse("handover_acknowledge", args=[handover.pk]))
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "noch nicht von dir best")

    def test_detail_shows_who_confirmed(self):
        handover = self.make_urgent()
        self.client.post(reverse("handover_acknowledge", args=[handover.pk]))
        response = self.client.get(reverse("handover_detail", args=[handover.pk]))
        self.assertContains(response, "Mara")
        self.assertContains(response, "als gelesen best")

    def test_acknowledging_a_foreign_station_entry_is_not_found(self):
        other = Station.objects.create(name="Fremd", slug="fremd-ack")
        handover = HandoverEntry.objects.create(
            station=other, category=HandoverEntry.Category.SAFETY,
            priority=HandoverEntry.Priority.URGENT,
            title="Fremd", details="x", author=self.user,
        )
        response = self.client.post(reverse("handover_acknowledge", args=[handover.pk]))
        self.assertEqual(response.status_code, 404)


class RetentionTests(PilotTestCase):
    def make_done_handover(self, days_ago):
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            status=HandoverEntry.Status.DONE,
            title=f"Erledigt vor {days_ago} Tagen",
            details="x",
            author=self.user,
        )
        moment = timezone.now() - timedelta(days=days_ago)
        HandoverEntry.objects.filter(pk=handover.pk).update(completed_at=moment)
        return handover

    def test_nothing_is_deleted_without_a_configured_period(self):
        self.make_done_handover(400)
        call_command("purge_expired")
        self.assertEqual(HandoverEntry.objects.count(), 1)

    def test_dry_run_reports_but_keeps_everything(self):
        self.make_done_handover(400)
        self.station.retention_handover_days = 30
        self.station.save(update_fields=["retention_handover_days"])
        call_command("purge_expired", "--dry-run")
        self.assertEqual(HandoverEntry.objects.count(), 1)

    def test_only_entries_past_the_period_are_deleted(self):
        old = self.make_done_handover(400)
        recent = self.make_done_handover(5)
        open_entry = HandoverEntry.objects.create(
            station=self.station, category=HandoverEntry.Category.TASK,
            title="Noch offen", details="x", author=self.user,
        )
        self.station.retention_handover_days = 30
        self.station.save(update_fields=["retention_handover_days"])

        call_command("purge_expired")

        self.assertFalse(HandoverEntry.objects.filter(pk=old.pk).exists())
        self.assertTrue(HandoverEntry.objects.filter(pk=recent.pk).exists())
        self.assertTrue(HandoverEntry.objects.filter(pk=open_entry.pk).exists())
        self.assertTrue(AuditEvent.objects.filter(action="retention.purged").exists())

    def test_coffee_entries_are_never_purged(self):
        CoffeeEntry.objects.create(
            station=self.station, member=self.user, amount_cents=500,
            reason="Einzahlung", created_by=self.user,
        )
        self.station.retention_handover_days = 1
        self.station.retention_audit_days = 1
        self.station.save(update_fields=["retention_handover_days", "retention_audit_days"])
        call_command("purge_expired")
        self.assertEqual(CoffeeEntry.objects.count(), 1)

    def test_other_stations_are_untouched(self):
        other = Station.objects.create(name="Andere", slug="andere")
        keeper = HandoverEntry.objects.create(
            station=other, category=HandoverEntry.Category.TASK,
            status=HandoverEntry.Status.DONE, title="Fremd", details="x", author=self.user,
        )
        HandoverEntry.objects.filter(pk=keeper.pk).update(
            completed_at=timezone.now() - timedelta(days=999)
        )
        self.station.retention_handover_days = 30
        self.station.save(update_fields=["retention_handover_days"])
        call_command("purge_expired")
        self.assertTrue(HandoverEntry.objects.filter(pk=keeper.pk).exists())


class TwoFactorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.password = "sicher-genug-123"
        self.user = User.objects.create_user(
            "tina@example.org", email="tina@example.org", password=self.password,
        )

    def enable_for(self, user):
        device = TotpDevice.objects.create(
            user=user, secret=pyotp.random_base32(), confirmed=True,
        )
        return device

    def current_code(self, device, offset=0):
        return pyotp.TOTP(device.secret).at(time.time() + offset)

    def login_password(self):
        return self.client.post(reverse("login"), {
            "username": "tina@example.org", "password": self.password,
        })

    def test_login_without_second_factor_is_unchanged(self):
        response = self.login_password()
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_password_alone_does_not_create_a_session(self):
        self.enable_for(self.user)
        response = self.login_password()
        self.assertRedirects(response, reverse("login_totp"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_correct_code_completes_the_login(self):
        device = self.enable_for(self.user)
        self.login_password()
        response = self.client.post(reverse("login_totp"), {
            "code": self.current_code(device),
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_code_keeps_the_door_shut(self):
        self.enable_for(self.user)
        self.login_password()
        response = self.client.post(reverse("login_totp"), {"code": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_code_cannot_be_replayed(self):
        device = self.enable_for(self.user)
        code = self.current_code(device)
        self.login_password()
        self.client.post(reverse("login_totp"), {"code": code})
        self.client.logout()

        self.login_password()
        response = self.client.post(reverse("login_totp"), {"code": code})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_code_page_is_useless_without_the_password_step(self):
        self.enable_for(self.user)
        response = self.client.get(reverse("login_totp"))
        self.assertRedirects(response, reverse("login"))

    def test_pending_login_expires(self):
        device = self.enable_for(self.user)
        self.login_password()
        session = self.client.session
        session["totp_pending_since"] = (
            timezone.now() - timedelta(minutes=10)
        ).isoformat()
        session.save()
        response = self.client.post(reverse("login_totp"), {
            "code": self.current_code(device),
        })
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_recovery_code_works_once(self):
        device = self.enable_for(self.user)
        codes = issue_recovery_codes(device)

        self.login_password()
        response = self.client.post(reverse("login_totp"), {"code": codes[0]})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.logout()

        self.login_password()
        response = self.client.post(reverse("login_totp"), {"code": codes[0]})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_recovery_codes_are_not_stored_in_plain_text(self):
        device = self.enable_for(self.user)
        codes = issue_recovery_codes(device)
        stored = list(device.recovery_codes.values_list("code_hash", flat=True))
        for code in codes:
            self.assertNotIn(code, stored)

    def test_setup_flow_enables_and_shows_recovery_codes(self):
        self.client.force_login(self.user)
        self.client.get(reverse("twofactor_setup"))
        secret = self.client.session["totp_setup_secret"]
        response = self.client.post(reverse("twofactor_setup"), {
            "code": pyotp.TOTP(secret).now(),
        })
        # Ohne fetch_redirect_response wuerde der Test die Einmal-Anzeige
        # selbst verbrauchen.
        self.assertRedirects(
            response, reverse("twofactor_codes"), fetch_redirect_response=False,
        )
        self.assertTrue(TotpDevice.objects.filter(user=self.user, confirmed=True).exists())

        codes_page = self.client.get(reverse("twofactor_codes"))
        self.assertEqual(codes_page.status_code, 200)
        self.assertEqual(len(codes_page.context["codes"]), 8)
        # Nur einmal sichtbar.
        self.assertRedirects(
            self.client.get(reverse("twofactor_codes")), reverse("twofactor_status")
        )
        self.assertTrue(AuditEvent.objects.filter(action="twofactor.enabled").exists())

    def test_setup_rejects_a_wrong_confirmation_code(self):
        self.client.force_login(self.user)
        self.client.get(reverse("twofactor_setup"))
        response = self.client.post(reverse("twofactor_setup"), {"code": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TotpDevice.objects.filter(user=self.user).exists())

    def test_disabling_requires_a_valid_code(self):
        device = self.enable_for(self.user)
        self.client.force_login(self.user)
        self.client.post(reverse("twofactor_disable"), {"code": "000000"})
        self.assertTrue(TotpDevice.objects.filter(user=self.user).exists())

        self.client.post(reverse("twofactor_disable"), {
            "code": self.current_code(device),
        })
        self.assertFalse(TotpDevice.objects.filter(user=self.user).exists())
        self.assertTrue(AuditEvent.objects.filter(action="twofactor.disabled").exists())


class LegalPagesTests(TestCase):
    def test_pages_are_reachable_without_login(self):
        for url_name in ("imprint", "privacy", "accessibility", "demo"):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)

    def test_demo_page_has_no_login_form_and_links_to_source(self):
        response = self.client.get(reverse("demo"))
        self.assertNotContains(response, "<form", html=False)
        self.assertContains(response, "AGPL")

    def test_access_page_links_to_demo(self):
        response = self.client.get(reverse("access"))
        self.assertContains(response, f'href="{reverse("demo")}"')

    def test_imprint_shows_placeholder_without_operator_settings(self):
        response = self.client.get(reverse("imprint"))
        self.assertContains(response, "[Betreiber")

    @override_settings(
        OPERATOR_NAME="Kreis Guetersloh",
        OPERATOR_ADDRESS="Postfach 1663, 33316 Guetersloh",
        OPERATOR_CONTACT="wachbuch@kreis-guetersloh.de",
    )
    def test_imprint_shows_configured_operator(self):
        response = self.client.get(reverse("imprint"))
        self.assertContains(response, "Kreis Guetersloh")
        self.assertNotContains(response, "[Betreiber")


class FeedTests(TestCase):
    def setUp(self):
        self.news = FeedSource.objects.create(
            name="Test RSS",
            url="https://www.guetersloh.de/feed.xml",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="Guetersloh",
            attribution="Test",
        )
        self.closures = FeedSource.objects.create(
            name="Test CSV",
            url="https://www.bielefeld01.de/data.csv",
            kind=FeedSource.Kind.CLOSURE_CSV,
            locality="Bielefeld",
            attribution="CC BY 4.0",
        )

    def test_rss_html_is_reduced_to_plain_text(self):
        payload = b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <item><title>Test &amp; Meldung</title><link>https://www.guetersloh.de/test</link>
        <description><![CDATA[<b>Sicher</b><script>alert(1)</script>]]></description>
        <pubDate>Tue, 28 Jul 2026 10:00:00 +0200</pubDate></item>
        </channel></rss>"""
        self.assertEqual(sync_rss(self.news, payload), 1)
        item = FeedItem.objects.get()
        self.assertNotIn("<script>", item.summary)
        self.assertIn("Sicher", item.summary)

    def test_dangerous_rss_link_is_removed(self):
        payload = b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <item><title>Boese URL</title><link>javascript:alert(1)</link>
        <description>Text</description></item></channel></rss>"""
        sync_rss(self.news, payload)
        self.assertEqual(FeedItem.objects.get().url, "")

    def test_closure_csv_schema_and_dates(self):
        payload = (
            "gid;strasse;ortsteil;beginn;ende;art_arb;art_vb;vonbis\n"
            "42;Teststrasse;Mitte;2026/07/28;2026/08/01;Kanalarbeiten;Vollsperrung;28.07.-01.08.\n"
        ).encode()
        self.assertEqual(sync_closure_csv(self.closures, payload), 1)
        item = FeedItem.objects.get()
        self.assertEqual(item.title, "Teststrasse - Mitte")
        self.assertEqual(item.starts_on.isoformat(), "2026-07-28")

    @override_settings(FEED_ALLOWED_HOSTS={"www.guetersloh.de"})
    def test_unlisted_feed_host_is_rejected_before_request(self):
        self.news.url = "https://attacker.invalid/feed.xml"
        with self.assertRaises(ValueError):
            fetch_source(self.news)

    @override_settings(FEED_ALLOWED_HOSTS={"feeds.example.org"})
    def test_feed_source_validation_requires_allowlisted_https_host(self):
        source = FeedSource(
            name="Nicht erlaubt",
            url="http://internal.example.org/feed.xml",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="Test",
            attribution="Test",
        )
        with self.assertRaises(ValidationError):
            source.full_clean()

    @override_settings(FEED_ALLOWED_HOSTS={"feeds.example.org"})
    def test_feed_connection_uses_the_validated_ip_address(self):
        source = FeedSource(
            name="Sicherer Feed",
            url="https://feeds.example.org/news.xml?region=nord",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="Test",
            attribution="Test",
        )
        with patch("core.net.socket.getaddrinfo") as lookup, patch(
            "core.net.urllib3.HTTPSConnectionPool"
        ) as pool_class:
            lookup.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
            response = pool_class.return_value.request.return_value
            response.status = 200
            response.stream.return_value = [b"payload"]
            self.assertEqual(fetch_source(source), b"payload")
        self.assertEqual(pool_class.call_args.args[0], "93.184.216.34")
        self.assertEqual(pool_class.call_args.kwargs["server_hostname"], "feeds.example.org")
        self.assertEqual(
            pool_class.return_value.request.call_args.args[:2],
            ("GET", "/news.xml?region=nord"),
        )

    def test_old_csv_items_are_removed_after_successful_import(self):
        FeedItem.objects.create(source=self.closures, external_id="old", title="Alt")
        payload = (
            "gid;strasse;ortsteil;beginn;ende;art_arb;art_vb;vonbis\n"
            "new;Neue Strasse;Mitte;2026/07/28;2026/08/01;Bau;;;\n"
        ).encode()
        sync_closure_csv(self.closures, payload)
        self.assertFalse(FeedItem.objects.filter(external_id="old").exists())
        self.assertTrue(FeedItem.objects.filter(external_id="new").exists())

    def test_waste_ics_keeps_future_pickups_and_drops_past_ones(self):
        waste_source = FeedSource.objects.create(
            name="Muellabfuhr Test",
            url="https://waste.example.org/cal.ics",
            kind=FeedSource.Kind.WASTE_ICS,
        )
        payload = (
            "BEGIN:VCALENDAR\nVERSION:2.0\n"
            "BEGIN:VEVENT\nUID:future-1\nDTSTART;VALUE=DATE:20991231\n"
            "SUMMARY:Restmuelltonne\nEND:VEVENT\n"
            "BEGIN:VEVENT\nUID:past-1\nDTSTART;VALUE=DATE:20200101\n"
            "SUMMARY:Alte Abholung\nEND:VEVENT\n"
            "END:VCALENDAR\n"
        ).encode()
        count = sync_waste_ics(waste_source, payload)
        self.assertEqual(count, 1)
        self.assertTrue(
            FeedItem.objects.filter(external_id="future-1", title="Restmuelltonne").exists()
        )
        self.assertFalse(FeedItem.objects.filter(external_id="past-1").exists())


class GeocodingTests(TestCase):
    @override_settings(GEOCODING_HOST="")
    def test_disabled_without_configured_host(self):
        with self.assertRaises(GeocodingError):
            lookup_district("Hauptstr. 1", "33397", "Steinhagen")

    @override_settings(GEOCODING_HOST="geo.example.org")
    def test_resolves_district_and_city_from_response(self):
        payload = json.dumps(
            [{"address": {"county": "Kreis Guetersloh", "town": "Steinhagen"}}]
        ).encode()
        with patch("core.geocoding.fetch_https", return_value=payload) as fetch:
            result = lookup_district("Hauptstr. 1", "33397", "Steinhagen")
        self.assertEqual(result, {"district": "Kreis Guetersloh", "city": "Steinhagen"})
        fetch.assert_called_once()

    @override_settings(GEOCODING_HOST="geo.example.org")
    def test_raises_when_address_not_found(self):
        with patch("core.geocoding.fetch_https", return_value=b"[]"):
            with self.assertRaises(GeocodingError):
                lookup_district("Nirgendwo", "", "")


class FeedFilteringTests(PilotTestCase):
    def test_feeds_filtered_by_station_locality_once_address_is_known(self):
        regional = FeedSource.objects.create(
            name="Regional", url="https://news.example.org/feed.xml",
            kind=FeedSource.Kind.NEWS_RSS, locality="Steinhagen", attribution="Test",
        )
        elsewhere = FeedSource.objects.create(
            name="Andernorts", url="https://news.example.org/other.xml",
            kind=FeedSource.Kind.NEWS_RSS, locality="Andernorts", attribution="Test",
        )
        FeedItem.objects.create(source=regional, external_id="1", title="Regional-Meldung")
        FeedItem.objects.create(source=elsewhere, external_id="2", title="Fremde Meldung")

        response = self.client.get(reverse("feeds"))
        self.assertContains(response, "Regional-Meldung")
        self.assertContains(response, "Fremde Meldung")

        self.station.city = "Steinhagen"
        self.station.save(update_fields=["city"])
        response = self.client.get(reverse("feeds"))
        self.assertContains(response, "Regional-Meldung")
        self.assertNotContains(response, "Fremde Meldung")


class TeamAndAuditTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])

    def test_station_admin_assigns_pending_tailscale_user(self):
        pending = User.objects.create_user(
            "pending@example.org", email="pending@example.org", first_name="Pia",
        )
        response = self.client.post(reverse("team_create"), {
            "email": "pending@example.org",
            "role": Membership.Role.SHIFT_LEAD,
        })
        self.assertRedirects(response, reverse("team"))
        assigned = Membership.objects.get(user=pending)
        self.assertEqual(assigned.station, self.station)
        self.assertEqual(assigned.role, Membership.Role.SHIFT_LEAD)
        self.assertTrue(AuditEvent.objects.filter(action="membership.created").exists())

    def test_grant_station_admin_does_not_grant_global_superuser(self):
        pending = User.objects.create_user("local-admin@example.org")
        call_command("grant_station_admin", pending.username)
        pending.refresh_from_db()
        self.assertFalse(pending.is_staff)
        self.assertFalse(pending.is_superuser)
        self.assertEqual(pending.station_memberships.get().role, Membership.Role.ADMIN)

    def test_admin_sets_coffee_payment_options(self):
        response = self.client.post(reverse("coffee_payment_update"), {
            "coffee_paypal_link": "https://paypal.me/testwache",
            "coffee_wero_link": "https://wero.example/testwache",
            "coffee_iban": "DE89 3704 0044 0532 0130 00",
            "coffee_account_holder": "Foerderverein Testwache",
        })
        self.assertRedirects(response, reverse("coffee"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.coffee_paypal_link, "https://paypal.me/testwache")
        self.assertEqual(self.station.coffee_iban, "DE89370400440532013000")
        self.assertTrue(AuditEvent.objects.filter(action="coffee.payment_settings_updated").exists())
        page = self.client.get(reverse("coffee"))
        self.assertContains(page, "paypal.me/testwache")
        self.assertContains(page, "Foerderverein Testwache")

    def test_settings_page_survives_unvalidated_iban_in_database(self):
        Station.objects.filter(pk=self.station.pk).update(coffee_iban="GARBAGE!!")
        response = self.client.post(reverse("station_settings"), {
            "name": "Wache Nord", "location": "", "street": "",
            "postal_code": "", "city": "", "district": "",
        })
        self.assertRedirects(response, reverse("station_settings"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, "Wache Nord")

    def test_long_grouped_iban_is_accepted(self):
        response = self.client.post(reverse("coffee_payment_update"), {
            "coffee_paypal_link": "", "coffee_wero_link": "",
            "coffee_iban": "MT84 MALT 0110 0001 2345 MTLC AST0 01S",
            "coffee_account_holder": "Testwache",
        })
        self.assertRedirects(response, reverse("coffee"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.coffee_iban, "MT84MALT011000012345MTLCAST001S")

    def test_invalid_iban_is_rejected(self):
        response = self.client.post(reverse("coffee_payment_update"), {
            "coffee_paypal_link": "",
            "coffee_wero_link": "",
            "coffee_iban": "not-an-iban",
            "coffee_account_holder": "Testwache",
        })
        self.assertRedirects(response, reverse("coffee"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.coffee_iban, "")

    def test_admin_sets_waste_calendar_url(self):
        with override_settings(FEED_ALLOWED_HOSTS={"waste.example.org"}):
            response = self.client.post(reverse("waste_source_update"), {
                "url": "https://waste.example.org/cal.ics",
            })
        self.assertRedirects(response, f"{reverse('feeds')}?typ=muell")
        source = FeedSource.objects.get(station=self.station, kind=FeedSource.Kind.WASTE_ICS)
        self.assertEqual(source.url, "https://waste.example.org/cal.ics")
        self.assertTrue(AuditEvent.objects.filter(action="feeds.waste_source_updated").exists())

    def test_waste_calendar_rejects_host_not_allowlisted(self):
        response = self.client.post(reverse("waste_source_update"), {
            "url": "https://attacker.invalid/cal.ics",
        })
        self.assertRedirects(response, f"{reverse('feeds')}?typ=muell")
        self.assertFalse(
            FeedSource.objects.filter(station=self.station, kind=FeedSource.Kind.WASTE_ICS).exists()
        )

    def test_member_cannot_configure_waste_calendar(self):
        self.membership.role = Membership.Role.MEMBER
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("waste_source_update"), {
            "url": "https://waste.example.org/cal.ics",
        })
        self.assertEqual(response.status_code, 403)

    def test_station_geocode_updates_city_and_district(self):
        self.station.street = "Hauptstr. 1"
        self.station.postal_code = "33397"
        self.station.save(update_fields=["street", "postal_code"])
        payload = json.dumps(
            [{"address": {"county": "Kreis Guetersloh", "town": "Steinhagen"}}]
        ).encode()
        with override_settings(GEOCODING_HOST="geo.example.org"), patch(
            "core.geocoding.fetch_https", return_value=payload
        ):
            response = self.client.post(reverse("station_geocode"))
        self.assertRedirects(response, reverse("station_settings"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.district, "Kreis Guetersloh")
        self.assertEqual(self.station.city, "Steinhagen")
        self.assertTrue(AuditEvent.objects.filter(action="station.geocoded").exists())

    @override_settings(GEOCODING_HOST="")
    def test_station_geocode_without_configured_host_shows_error(self):
        response = self.client.post(reverse("station_geocode"), follow=True)
        self.assertContains(response, "Kein Geocoding-Dienst konfiguriert")

    def test_auditor_sees_audit_but_not_dashboard(self):
        self.membership.role = Membership.Role.AUDITOR
        self.membership.save(update_fields=["role"])
        AuditEvent.objects.create(
            actor=self.user,
            station=self.station,
            action="test.event",
            object_type="Test",
        )
        self.assertEqual(self.client.get(reverse("audit_log")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 403)

    def test_admin_configures_station_modules_with_audit_event(self):
        response = self.client.post(reverse("station_settings"), {
            "name": "Wache Nord",
            "calendar_enabled": "on",
            "coffee_enabled": "on",
        })
        self.assertRedirects(response, reverse("station_settings"))
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, "Wache Nord")
        self.assertFalse(self.station.birthdays_enabled)
        self.assertFalse(self.station.feeds_enabled)
        self.assertTrue(AuditEvent.objects.filter(
            action="station.settings_updated",
            station=self.station,
        ).exists())

    def test_disabled_module_is_hidden_and_returns_not_found(self):
        self.station.coffee_enabled = False
        self.station.save(update_fields=["coffee_enabled"])
        response = self.client.get(reverse("more"))
        self.assertNotContains(response, "Kaffeekasse")
        self.assertEqual(self.client.get(reverse("coffee")).status_code, 404)

    def test_admin_cannot_remove_own_admin_role(self):
        response = self.client.post(reverse("membership_update", args=[self.membership.pk]), {
            "role": Membership.Role.MEMBER,
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, Membership.Role.ADMIN)
        self.assertContains(response, "eigene Adminrolle")

    def test_django_admin_cannot_bypass_handover_audit(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            title="Nicht direkt aendern",
            details="Testinhalt",
            author=self.user,
        )
        response = self.client.post(
            reverse("admin:core_handoverentry_change", args=[handover.pk]),
            {"title": "Umgangen"},
        )
        self.assertEqual(response.status_code, 403)
        handover.refresh_from_db()
        self.assertEqual(handover.title, "Nicht direkt aendern")
