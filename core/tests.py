from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .feed_sync import fetch_source, sync_closure_csv, sync_rss
from .models import (
    AuditEvent,
    BirthdayPreference,
    CalendarEvent,
    CalendarFeedToken,
    CoffeeEntry,
    FeedItem,
    FeedSource,
    HandoverEntry,
    HandoverRevision,
    Membership,
    PushSubscription,
    Station,
    StationTask,
    StationTaskCompletion,
    TotpDevice,
)


class PilotTestCase(TestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Testwache",
            slug="testwache",
            feeds_enabled=True,
        )
        self.user = User.objects.create_user("member@example.org", first_name="Mara")
        self.membership = Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        self.client.force_login(self.user)


class ProgressiveWebAppTests(PilotTestCase):
    def test_manifest_is_installable(self):
        response = self.client.get(reverse("web_manifest"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["display"], "standalone")
        self.assertEqual(payload["name"], "Wachbuch")
        self.assertEqual(payload["short_name"], "Wachbuch")
        self.assertEqual(payload["start_url"], reverse("dashboard"))
        self.assertTrue(payload["icons"])
        self.assertTrue(any(item["name"] == "Tagesaufgaben" for item in payload["shortcuts"]))

    def test_shell_brand_uses_station_subtitle(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "<strong>Wachbuch</strong>", html=False)
        self.assertContains(response, self.station.name)
        self.assertContains(response, 'name="apple-mobile-web-app-title" content="Wachbuch"')
        self.assertNotContains(response, "<small>Rettungswache</small>")

    def test_service_worker_and_offline_page_are_available(self):
        worker = self.client.get(reverse("service_worker"))
        self.assertEqual(worker.status_code, 200)
        self.assertIn("javascript", worker["Content-Type"])
        self.assertEqual(worker["Service-Worker-Allowed"], "/")
        self.assertContains(worker, reverse("offline"))
        offline = self.client.get(reverse("offline"))
        self.assertEqual(offline.status_code, 200)
        self.assertContains(offline, "Offline")
        self.assertContains(offline, "nicht möglich")

    def test_shell_exposes_manifest_and_urgent_nav_badge(self):
        HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            priority=HandoverEntry.Priority.URGENT,
            title="Dringend im Badge",
            details="Bitte beachten",
            author=self.user,
        )
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, reverse("web_manifest"))
        self.assertContains(response, 'name="apple-mobile-web-app-capable"')
        self.assertContains(response, "nav-badge")
        self.assertContains(response, "1")


class SecurityAndAccessTests(PilotTestCase):
    def test_health_endpoint_and_security_headers(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["version"], "0.15.0")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("publickey-credentials-get=(self)", response.headers["Permissions-Policy"])

    def test_privacy_page_lists_essential_cookies_only(self):
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rwsth_session")
        self.assertContains(response, "rwsth_csrf")
        self.assertContains(response, "TDDDG")
        self.assertContains(response, "AI Act")
        self.assertContains(response, "Version 0.15.0")
        self.assertNotContains(response, "Google Analytics")

    def test_landing_presents_project_before_login(self):
        self.client.logout()
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wachbuch")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, "Zugang nach Login und Freigabe")
        self.assertContains(response, "Master-Admin")
        self.assertNotContains(response, reverse("register"))
        self.assertNotContains(response, "Tailscale")

    def test_authenticated_member_is_routed_from_landing_to_dashboard(self):
        response = self.client.get(reverse("landing"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_unauthenticated_app_routes_redirect_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_user_without_membership_waits_for_approval(self):
        outsider = User.objects.create_user("outside@example.org")
        self.client.force_login(outsider)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("access"))
        access = self.client.get(reverse("access"))
        self.assertEqual(access.status_code, 200)
        self.assertContains(access, "Freigabe")

    def test_auditor_cannot_read_station_content(self):
        self.membership.role = Membership.Role.AUDITOR
        self.membership.save(update_fields=["role"])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_page_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("access"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('access')}",
        )

    def test_password_login_reaches_dashboard(self):
        User.objects.create_user("login@example.org", password="correct-password-1")
        Membership.objects.create(
            user=User.objects.get(username="login@example.org"),
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        self.client.logout()
        response = self.client.post(reverse("login"), {
            "username": "login@example.org",
            "password": "correct-password-1",
        })
        self.assertRedirects(
            response,
            reverse("landing"),
            target_status_code=302,
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_authenticated_user_can_log_out_from_interface(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, reverse("logout"))
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("landing"))
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
        self.assertContains(response, "Schnellzugriff")
        self.assertContains(response, reverse("handover_list") + "?ansicht=dringend")
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

    def test_calendar_event_ics_download(self):
        event = CalendarEvent.objects.create(
            station=self.station,
            title="Übung Wache",
            description="Nur Organisation",
            starts_at=timezone.now() + timedelta(hours=2),
            ends_at=timezone.now() + timedelta(hours=3),
            created_by=self.user,
        )
        response = self.client.get(reverse("calendar_event_ics", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/calendar", response["Content-Type"])
        self.assertIn("BEGIN:VEVENT", response.content.decode())
        self.assertIn("Übung Wache", response.content.decode())
        self.assertIn("attachment", response["Content-Disposition"])

    def test_more_page_holds_secondary_modules(self):
        response = self.client.get(reverse("more"))
        self.assertContains(response, "Tagesaufgaben")
        self.assertContains(response, "Geburtstage")
        self.assertContains(response, "Kaffeekasse")
        self.assertContains(response, "Meldungen &amp; Verkehr", html=True)

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
            reverse("tasks_today"),
            reverse("tasks_week"),
            reverse("more"),
            reverse("team"),
            reverse("team_user_create"),
            reverse("team_create"),
            reverse("membership_update", args=[self.membership.pk]),
            reverse("station_settings"),
            reverse("audit_log"),
            reverse("tasks_manage"),
            reverse("task_create"),
            reverse("account_home"),
            reverse("chat"),
            reverse("crypto_setup"),
            reverse("private_chat_home"),
            reverse("secure_mail_inbox"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.count(b"<h1"), 1)


class StationTaskBoardTests(PilotTestCase):
    def test_default_template_and_completion_toggle(self):
        response = self.client.get(reverse("tasks_today"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tägliche Routine")
        self.assertContains(response, "Fahrzeugcheck")
        self.assertContains(response, "Wochentagsaufgabe")
        task = StationTask.objects.get(station=self.station, title="Fahrzeugcheck")
        done = self.client.post(reverse("task_toggle", args=[task.pk]), {
            "tag": timezone.localdate().isoformat(),
            "erledigt": "1",
            "next": reverse("tasks_today"),
        })
        self.assertRedirects(done, reverse("tasks_today"))
        self.assertTrue(
            StationTaskCompletion.objects.filter(task=task, work_date=timezone.localdate()).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action="station_task.completed").exists())

    def test_week_board_and_manage_permissions(self):
        self.client.get(reverse("tasks_today"))
        week = self.client.get(reverse("tasks_week"))
        self.assertEqual(week.status_code, 200)
        self.assertContains(week, "Wochenbogen")
        self.assertEqual(self.client.get(reverse("tasks_manage")).status_code, 403)
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        manage = self.client.get(reverse("tasks_manage"))
        self.assertEqual(manage.status_code, 200)
        self.assertContains(manage, "Aufgaben-Vorlage")

    def test_disabled_tasks_module_is_hidden(self):
        self.station.tasks_enabled = False
        self.station.save(update_fields=["tasks_enabled"])
        self.assertEqual(self.client.get(reverse("tasks_today")).status_code, 404)
        self.assertNotContains(self.client.get(reverse("more")), "Tagesaufgaben")


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

    def test_birthday_without_consent_does_not_persist_date(self):
        response = self.client.post(reverse("birthday_settings"), {
            "day": 14,
            "month": 6,
        })
        self.assertRedirects(response, reverse("birthdays"))
        preference = BirthdayPreference.objects.get(user=self.user, station=self.station)
        self.assertFalse(preference.is_visible)
        self.assertIsNone(preference.day)
        self.assertIsNone(preference.month)
        self.assertIsNone(preference.consented_at)

    def test_birthday_rejects_impossible_calendar_date(self):
        response = self.client.post(reverse("birthday_settings"), {
            "day": 31,
            "month": 2,
            "consent": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "kein gültiges Datum")
        self.assertFalse(
            BirthdayPreference.objects.filter(
                user=self.user,
                station=self.station,
                is_visible=True,
            ).exists()
        )

    def test_upcoming_birthdays_hide_inactive_members(self):
        BirthdayPreference.objects.create(
            user=self.user,
            station=self.station,
            day=1,
            month=1,
            is_visible=True,
            consented_at=timezone.now(),
        )
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        from .views import upcoming_birthdays

        self.assertEqual(upcoming_birthdays(self.station), [])

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

    def test_coffee_correct_view_rejects_second_correction(self):
        self.membership.role = Membership.Role.CASHIER
        self.membership.save(update_fields=["role"])
        original = CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=500,
            reason="Einzahlung",
            created_by=self.user,
        )
        first = self.client.post(reverse("coffee_correct", args=[original.pk]), {
            "reason": "Falscher Betrag",
        })
        self.assertRedirects(first, reverse("coffee"))
        second = self.client.post(reverse("coffee_correct", args=[original.pk]), {
            "reason": "Nochmals",
        })
        self.assertRedirects(second, reverse("coffee"))
        self.assertEqual(CoffeeEntry.objects.filter(correction_of=original).count(), 1)


class FeedTests(PilotTestCase):
    def setUp(self):
        super().setUp()
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
        with patch("core.feed_sync.socket.getaddrinfo") as lookup, patch(
            "core.feed_sync.urllib3.HTTPSConnectionPool"
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

    def test_feeds_view_hides_disabled_sources_and_names_coverage_gap(self):
        FeedItem.objects.create(
            source=self.news,
            external_id="live",
            title="Aktive Meldung",
        )
        self.news.is_enabled = False
        self.news.save(update_fields=["is_enabled"])
        FeedItem.objects.create(
            source=self.news,
            external_id="disabled",
            title="Deaktivierte Meldung",
        )
        enabled = FeedSource.objects.create(
            name="Aktive Quelle",
            url="https://www.guetersloh.de/active.xml",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="GT",
            attribution="Test",
            is_enabled=True,
        )
        FeedItem.objects.create(
            source=enabled,
            external_id="visible",
            title="Sichtbare Meldung",
        )
        news_page = self.client.get(reverse("feeds"))
        self.assertEqual(news_page.status_code, 200)
        self.assertContains(news_page, "Sichtbare Meldung")
        self.assertNotContains(news_page, "Deaktivierte Meldung")
        traffic = self.client.get(reverse("feeds") + "?typ=verkehr")
        self.assertEqual(traffic.status_code, 200)
        self.assertContains(traffic, "kein gleichwertiger vollständiger Baustellenfeed")


class TeamAndAuditTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])

    def test_station_admin_assigns_pending_local_user(self):
        pending = User.objects.create_user("pending@example.org", first_name="Pia")
        response = self.client.post(reverse("team_create"), {
            "user": pending.pk,
            "role": Membership.Role.SHIFT_LEAD,
        })
        self.assertRedirects(response, reverse("team"))
        assigned = Membership.objects.get(user=pending)
        self.assertEqual(assigned.station, self.station)
        self.assertEqual(assigned.role, Membership.Role.SHIFT_LEAD)
        self.assertTrue(AuditEvent.objects.filter(action="membership.created").exists())

    def test_station_admin_reactivates_inactive_membership(self):
        pending = User.objects.create_user("returning@example.org", first_name="Rita")
        Membership.objects.create(
            user=pending,
            station=self.station,
            role=Membership.Role.MEMBER,
            is_active=False,
        )
        response = self.client.post(reverse("team_create"), {
            "user": pending.pk,
            "role": Membership.Role.CASHIER,
        })
        self.assertRedirects(response, reverse("team"))
        membership = Membership.objects.get(user=pending, station=self.station)
        self.assertTrue(membership.is_active)
        self.assertEqual(membership.role, Membership.Role.CASHIER)
        self.assertEqual(Membership.objects.filter(user=pending, station=self.station).count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="membership.reactivated").exists())

    def test_grant_station_admin_does_not_grant_global_superuser(self):
        pending = User.objects.create_user("local-admin@example.org")
        call_command("grant_station_admin", pending.username)
        pending.refresh_from_db()
        self.assertFalse(pending.is_staff)
        self.assertFalse(pending.is_superuser)
        self.assertEqual(pending.station_memberships.get().role, Membership.Role.ADMIN)

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
        self.assertContains(response, "eigene Master-Admin-Rolle")

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


class RetentionAuditExitAndMfaTests(PilotTestCase):
    def test_deactivating_membership_withdraws_birthday(self):
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        member = User.objects.create_user("leaving@example.org", first_name="Lea")
        target = Membership.objects.create(
            user=member,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        BirthdayPreference.objects.create(
            user=member,
            station=self.station,
            day=12,
            month=5,
            is_visible=True,
            consented_at=timezone.now(),
        )
        response = self.client.post(reverse("membership_update", args=[target.pk]), {
            "role": Membership.Role.MEMBER,
        })
        self.assertRedirects(response, reverse("team"))
        pref = BirthdayPreference.objects.get(user=member, station=self.station)
        self.assertFalse(pref.is_visible)
        self.assertIsNone(pref.day)
        self.assertTrue(AuditEvent.objects.filter(action="birthday.withdrawn_on_exit").exists())
        event = AuditEvent.objects.filter(action="membership.updated").latest("created_at")
        self.assertEqual(event.metadata["changes"]["is_active"]["from"], True)
        self.assertEqual(event.metadata["changes"]["is_active"]["to"], False)

    def test_handover_content_edit_creates_revision_without_free_text_audit(self):
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            title="Alter Titel",
            details="Alter Text",
            author=self.user,
        )
        HandoverRevision.objects.create(
            handover=handover,
            version=1,
            snapshot={"category": "station", "priority": "normal", "status": "open",
                      "title": "Alter Titel", "details": "Alter Text"},
            changed_by=self.user,
        )
        response = self.client.post(reverse("handover_edit", args=[handover.pk]), {
            "category": HandoverEntry.Category.TASK,
            "priority": HandoverEntry.Priority.IMPORTANT,
            "title": "Neuer Titel",
            "details": "Neuer geheimer Freitext",
        })
        self.assertRedirects(response, reverse("handover_detail", args=[handover.pk]))
        handover.refresh_from_db()
        self.assertEqual(handover.version, 2)
        self.assertEqual(handover.title, "Neuer Titel")
        self.assertEqual(handover.revisions.count(), 2)
        event = AuditEvent.objects.get(action="handover.content_updated")
        self.assertIn("category", event.metadata["changes"])
        self.assertNotIn("Neuer geheimer Freitext", str(event.metadata))
        self.assertNotIn("Alter Text", str(event.metadata))

    @override_settings(RETENTION_FEED_DAYS=14, RETENTION_AUDIT_DAYS=0)
    def test_feed_retention_removes_stale_items(self):
        source = FeedSource.objects.create(
            name="Retention RSS",
            url="https://example.org/rss.xml",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="Test",
            attribution="Test",
        )
        stale = FeedItem.objects.create(
            source=source,
            external_id="old",
            title="Alt",
            last_seen_at=timezone.now() - timedelta(days=30),
        )
        fresh = FeedItem.objects.create(
            source=source,
            external_id="new",
            title="Neu",
            last_seen_at=timezone.now(),
        )
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("apply_retention", stdout=out)
        self.assertFalse(FeedItem.objects.filter(pk=stale.pk).exists())
        self.assertTrue(FeedItem.objects.filter(pk=fresh.pk).exists())

    def test_feed_upsert_keeps_first_imported_at(self):
        source = FeedSource.objects.create(
            name="Upsert RSS",
            url="https://example.org/news.xml",
            kind=FeedSource.Kind.NEWS_RSS,
            locality="Test",
            attribution="Test",
        )
        first = timezone.now() - timedelta(days=2)
        item = FeedItem.objects.create(
            source=source,
            external_id="same",
            title="Eins",
            first_imported_at=first,
            last_seen_at=first,
        )
        from .feed_sync import upsert_feed_item

        upsert_feed_item(source, "same", title="Zwei", summary="", url="")
        item.refresh_from_db()
        self.assertEqual(item.title, "Zwei")
        self.assertEqual(item.first_imported_at, first)
        self.assertGreater(item.last_seen_at, first)

    def test_station_settings_audit_contains_structure_diff(self):
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("station_settings"), {
            "name": "Wache Diff",
            "calendar_enabled": "on",
            "coffee_enabled": "on",
            "tasks_enabled": "on",
        })
        self.assertRedirects(response, reverse("station_settings"))
        event = AuditEvent.objects.filter(action="station.settings_updated").latest("created_at")
        self.assertIn("name", event.metadata["changes"])
        self.assertEqual(event.metadata["changes"]["name"]["to"], "Wache Diff")

    def test_mfa_login_requires_totp_code(self):
        import pyotp

        password = "correct-password-1"
        user = User.objects.create_user("mfa@example.org", password=password)
        Membership.objects.create(
            user=user,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        secret = pyotp.random_base32()
        TotpDevice.objects.create(
            user=user,
            secret=secret,
            is_confirmed=True,
            confirmed_at=timezone.now(),
        )
        self.client.logout()
        response = self.client.post(reverse("login"), {
            "username": "mfa@example.org",
            "password": password,
        })
        self.assertRedirects(response, reverse("mfa_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)
        bad = self.client.post(reverse("mfa_verify"), {"token": "000000"})
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "ungültig")
        good = self.client.post(reverse("mfa_verify"), {
            "token": pyotp.TOTP(secret).now(),
        })
        self.assertEqual(good.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)


class PasskeyPushCalendarTests(PilotTestCase):
    def test_passkey_endpoints_unavailable_without_rp_config(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("passkey_login_options")).status_code, 404)

    @override_settings(WEBAUTHN_ENABLED=True, WEBAUTHN_RP_ID="localhost", WEBAUTHN_ORIGIN="http://localhost")
    def test_passkey_login_options_available_when_configured(self):
        self.client.logout()
        response = self.client.get(reverse("passkey_login_options"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("challenge", payload)

    def test_station_calendar_feed_and_token(self):
        CalendarEvent.objects.create(
            station=self.station,
            title="Probe",
            description="Test",
            starts_at=timezone.now() + timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=2),
            created_by=self.user,
        )
        feed = self.client.get(reverse("calendar_feed_ics"))
        self.assertEqual(feed.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", feed.content.decode())
        self.assertIn("Probe", feed.content.decode())
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        create = self.client.post(reverse("calendar_feed_manage"), {
            "action": "create",
            "label": "Tablet",
        })
        self.assertRedirects(create, reverse("calendar_feed_manage"))
        token = CalendarFeedToken.objects.get(station=self.station)
        self.client.logout()
        public = self.client.get(reverse("calendar_feed_token_ics", args=[token.token]))
        self.assertEqual(public.status_code, 200)
        self.assertIn("Probe", public.content.decode())

    def test_push_settings_hidden_when_disabled(self):
        self.assertEqual(self.client.get(reverse("push_settings")).status_code, 404)

    @override_settings(
        WEB_PUSH_ENABLED=True,
        VAPID_PUBLIC_KEY="BPtest",
        VAPID_PRIVATE_KEY="private",
    )
    def test_push_subscription_can_be_stored(self):
        response = self.client.post(
            reverse("push_settings"),
            data=json.dumps({
                "endpoint": "https://push.example/subscription/1",
                "keys": {"p256dh": "abc", "auth": "def"},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(user=self.user).exists())

    def test_urgent_push_noop_when_disabled(self):
        from .push import notify_urgent_handover

        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.TASK,
            priority=HandoverEntry.Priority.URGENT,
            title="Dringend",
            details="x",
            author=self.user,
        )
        self.assertEqual(notify_urgent_handover(handover, self.user), 0)


class RegistrationAccountChatTests(PilotTestCase):
    @override_settings(REGISTRATION_ENABLED=True)
    def test_self_registration_waits_for_admin_approval(self):
        self.client.logout()
        response = self.client.post(reverse("register"), {
            "username": "neu@example.org",
            "first_name": "Neu",
            "preferred_station": self.station.pk,
            "note": "Schicht Team A",
            "password1": "StrongPass-12345",
            "password2": "StrongPass-12345",
        })
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="neu@example.org")
        from .models import RegistrationRequest

        request_row = RegistrationRequest.objects.get(user=user)
        self.assertEqual(request_row.status, RegistrationRequest.Status.PENDING)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("access"))
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        self.client.force_login(self.user)
        approve = self.client.post(reverse("team_create"), {
            "user": user.pk,
            "role": Membership.Role.MEMBER,
        })
        self.assertRedirects(approve, reverse("team"))
        request_row.refresh_from_db()
        self.assertEqual(request_row.status, RegistrationRequest.Status.APPROVED)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_master_admin_creates_user_with_membership(self):
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])
        response = self.client.post(reverse("team_user_create"), {
            "username": "kollege@example.org",
            "first_name": "Kim",
            "last_name": "Kollege",
            "password1": "StrongPass-12345",
            "password2": "StrongPass-12345",
            "role": Membership.Role.MEMBER,
        })
        self.assertRedirects(response, reverse("team"))
        created = User.objects.get(username="kollege@example.org")
        membership = Membership.objects.get(user=created, station=self.station)
        self.assertTrue(membership.is_active)
        self.assertEqual(membership.role, Membership.Role.MEMBER)
        self.assertTrue(AuditEvent.objects.filter(action="membership.user_created").exists())
        self.client.force_login(created)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_account_home_updates_profile(self):
        response = self.client.post(reverse("account_home"), {
            "action": "profile",
            "profile-first_name": "Mara",
            "profile-last_name": "Muster",
            "profile-email": "mara@example.org",
        })
        self.assertRedirects(response, reverse("account_home"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "Muster")

    def test_account_avatar_upload_and_serve(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from .models import UserProfile

        png = BytesIO()
        Image.new("RGB", (80, 80), color=(30, 90, 50)).save(png, format="PNG")
        upload = SimpleUploadedFile("avatar.png", png.getvalue(), content_type="image/png")
        response = self.client.post(reverse("account_home"), {
            "action": "avatar",
            "avatar-avatar": upload,
        })
        self.assertRedirects(response, reverse("account_home"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.has_avatar)
        image = self.client.get(reverse("avatar_image", args=[self.user.pk]))
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/jpeg")

    def test_chat_rejects_plaintext_posts(self):
        response = self.client.post(reverse("chat"), {"body": "Bitte Lager prüfen"})
        self.assertRedirects(response, reverse("chat"))
        from .models import ChatMessage

        self.assertFalse(ChatMessage.objects.exists())

    def test_encrypted_station_chat_stores_ciphertext_only(self):
        from .models import ChatMessage, UserCryptoIdentity

        UserCryptoIdentity.objects.create(
            user=self.user,
            public_jwk={"kty": "EC", "crv": "P-256", "x": "abc", "y": "def"},
            wrapped_private_jwk="a" * 40,
            kdf_salt="b" * 24,
        )
        payload = {
            "ciphertext": "Y2lwaGVydGV4dA",
            "nonce": "bm9uY2Vub25jZQ",
            "key_wraps": {
                str(self.user.pk): {
                    "epk": {"kty": "EC", "crv": "P-256", "x": "eHg", "y": "eXk"},
                    "wrapped_key": "aXY.d3JhcA",
                }
            },
        }
        response = self.client.post(
            reverse("chat"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        message = ChatMessage.objects.get()
        self.assertTrue(message.is_encrypted)
        self.assertEqual(message.body, "")
        self.assertEqual(message.ciphertext, "Y2lwaGVydGV4dA")
        self.assertNotIn("Bitte", message.ciphertext)

    def test_secure_mail_not_readable_by_master_admin_outsider(self):
        from .models import SecureMail, SecureMailRecipient, UserCryptoIdentity

        admin_user = User.objects.create_user("master@example.org", first_name="Master")
        Membership.objects.create(
            user=admin_user,
            station=self.station,
            role=Membership.Role.ADMIN,
        )
        peer = User.objects.create_user("peer@example.org", first_name="Peer")
        Membership.objects.create(
            user=peer,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        for user in (self.user, peer):
            UserCryptoIdentity.objects.create(
                user=user,
                public_jwk={"kty": "EC", "crv": "P-256", "x": "abc", "y": "def"},
                wrapped_private_jwk="a" * 40,
                kdf_salt="b" * 24,
            )
        mail = SecureMail.objects.create(
            station=self.station,
            sender=self.user,
            ciphertext="Y2lwaGVy",
            nonce="bm9uY2U",
            key_wraps={
                str(self.user.pk): {
                    "epk": {"kty": "EC", "crv": "P-256", "x": "eHg", "y": "eXk"},
                    "wrapped_key": "aXY.d3JhcA",
                },
                str(peer.pk): {
                    "epk": {"kty": "EC", "crv": "P-256", "x": "eHg", "y": "eXk"},
                    "wrapped_key": "aXY.d3JhcA",
                },
            },
        )
        SecureMailRecipient.objects.create(mail=mail, user=peer)
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get(reverse("secure_mail_detail", args=[mail.pk])).status_code, 404)
        self.client.force_login(peer)
        self.assertEqual(self.client.get(reverse("secure_mail_detail", args=[mail.pk])).status_code, 200)

    def test_private_conversation_hidden_from_non_participants(self):
        from .models import PrivateConversation, PrivateMessage

        peer = User.objects.create_user("peer2@example.org")
        Membership.objects.create(user=peer, station=self.station, role=Membership.Role.MEMBER)
        outsider = User.objects.create_user("outsider@example.org")
        Membership.objects.create(
            user=outsider,
            station=self.station,
            role=Membership.Role.ADMIN,
        )
        low, high = sorted([self.user.pk, peer.pk])
        conversation = PrivateConversation.objects.create(
            station=self.station,
            user_low_id=low,
            user_high_id=high,
        )
        PrivateMessage.objects.create(
            conversation=conversation,
            author=self.user,
            ciphertext="Y2lwaGVy",
            nonce="bm9uY2U",
            key_wraps={
                str(self.user.pk): {
                    "epk": {"kty": "EC", "crv": "P-256", "x": "eHg", "y": "eXk"},
                    "wrapped_key": "aXY.d3JhcA",
                },
                str(peer.pk): {
                    "epk": {"kty": "EC", "crv": "P-256", "x": "eHg", "y": "eXk"},
                    "wrapped_key": "aXY.d3JhcA",
                },
            },
        )
        self.client.force_login(outsider)
        self.assertEqual(
            self.client.get(reverse("private_chat_thread", args=[conversation.pk])).status_code,
            404,
        )
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(reverse("private_chat_thread", args=[conversation.pk])).status_code,
            200,
        )


class HolidayCalendarTests(PilotTestCase):
    def test_nrw_holidays_for_2026(self):
        from datetime import date

        from .holidays import nrw_holidays_for_year

        titles = {holiday.title: holiday.day for holiday in nrw_holidays_for_year(2026)}
        self.assertEqual(titles["Neujahr"], date(2026, 1, 1))
        self.assertEqual(titles["Karfreitag"], date(2026, 4, 3))
        self.assertEqual(titles["Ostermontag"], date(2026, 4, 6))
        self.assertEqual(titles["Christi Himmelfahrt"], date(2026, 5, 14))
        self.assertEqual(titles["Pfingstmontag"], date(2026, 5, 25))
        self.assertEqual(titles["Fronleichnam"], date(2026, 6, 4))
        self.assertEqual(len(titles), 11)

    def test_calendar_lists_nrw_holidays(self):
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "gesetzliche Feiertage (NRW)")
        self.assertTrue(any(item.kind == "holiday" for item in response.context["page_obj"]))
        self.assertContains(response, "Feiertag")

    def test_holidays_can_be_disabled(self):
        self.station.holidays_enabled = False
        self.station.save(update_fields=["holidays_enabled"])
        response = self.client.get(reverse("calendar"))
        self.assertFalse(any(item.kind == "holiday" for item in response.context["page_obj"]))
        feed = self.client.get(reverse("calendar_feed_ics"))
        self.assertNotIn("wachbuch-holiday-", feed.content.decode())

    def test_ics_includes_all_day_holidays(self):
        feed = self.client.get(reverse("calendar_feed_ics"))
        body = feed.content.decode()
        self.assertEqual(feed.status_code, 200)
        self.assertIn("VALUE=DATE:", body)
        self.assertIn("wachbuch-holiday-", body)
        self.assertIn("TRANSP:TRANSPARENT", body)
        self.assertIn("Gesetzlicher Feiertag", body)

    def test_all_day_holiday_counts_as_upcoming_after_noon(self):
        from datetime import datetime, time

        from .holidays import AgendaEntry, is_upcoming_agenda_item

        today = timezone.localdate()
        noon = timezone.make_aware(datetime.combine(today, time(15, 0)))
        holiday = AgendaEntry(
            starts_at=timezone.make_aware(datetime.combine(today, time.min)),
            ends_at=timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min)),
            title="Testfeiertag",
            kind="holiday",
            all_day=True,
        )
        self.assertTrue(is_upcoming_agenda_item(holiday, now=noon, today=today))
        past_event = AgendaEntry(
            starts_at=noon - timedelta(hours=2),
            ends_at=noon + timedelta(hours=1),
            title="Laufend",
            kind="event",
        )
        self.assertFalse(is_upcoming_agenda_item(past_event, now=noon, today=today))


class ApiMobileFoundationTests(PilotTestCase):
    def _create_token(self):
        from .api.views import generate_api_token
        from .models import ApiToken

        raw, token_hash, prefix = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            label="Test App",
            token_prefix=prefix,
            token_hash=token_hash,
            scopes=["read:me", "read:handovers"],
        )
        return raw, token

    def test_api_root_and_openapi_are_public(self):
        root = self.client.get(reverse("api_v1_root"))
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["api_version"], "v1")
        schema = self.client.get(reverse("api_v1_openapi"))
        self.assertEqual(schema.status_code, 200)
        self.assertIn("openapi:", schema.content.decode())

    def test_token_exchange_and_me_endpoint(self):
        password = "StrongPass-12345"
        self.user.set_password(password)
        self.user.save()
        response = self.client.post(
            reverse("api_v1_token"),
            data=json.dumps({"username": self.user.username, "password": password, "label": "CLI"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]
        me = self.client.get(
            reverse("api_v1_me"),
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["username"], self.user.username)
        self.assertEqual(me.json()["membership"]["station"]["slug"], self.station.slug)

    def test_handovers_require_token_and_respect_station(self):
        raw, _token = self._create_token()
        HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.NORMAL,
            title="Material nachlegen",
            details="Ohne Patientendaten",
            author=self.user,
        )
        denied = self.client.get(reverse("api_v1_handovers"))
        self.assertEqual(denied.status_code, 401)
        ok = self.client.get(
            reverse("api_v1_handovers"),
            HTTP_AUTHORIZATION=f"Bearer {raw}",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["count"], 1)
        self.assertEqual(ok.json()["results"][0]["title"], "Material nachlegen")

    def test_account_ui_creates_revocable_token(self):
        create = self.client.post(reverse("api_tokens_manage"), {
            "action": "create",
            "label": "iOS",
        })
        self.assertEqual(create.status_code, 200)
        self.assertIsNotNone(create.context["plaintext_token"])
        self.assertTrue(create.context["mobile_setup_url"])
        from .models import ApiToken

        token = ApiToken.objects.get(user=self.user, label="iOS")
        revoke = self.client.post(reverse("api_tokens_manage"), {
            "action": "revoke",
            "token_id": token.pk,
        })
        self.assertRedirects(revoke, reverse("api_tokens_manage"))
        token.refresh_from_db()
        self.assertFalse(token.is_active)

    def test_mobile_setup_qr_png(self):
        response = self.client.get(reverse("mobile_setup_qr"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertGreater(len(response.content), 100)


class ApiUnifiedContractTests(PilotTestCase):
    """Widerrufbare Tokens + deutsche Aliase + Schreibpfade (PR#10 ∪ PR#12)."""

    def _token(self, scopes=None):
        from .api.views import DEFAULT_MOBILE_SCOPES, generate_api_token
        from .models import ApiToken

        raw, token_hash, prefix = generate_api_token()
        ApiToken.objects.create(
            user=self.user,
            label="Unified",
            token_prefix=prefix,
            token_hash=token_hash,
            scopes=list(scopes if scopes is not None else DEFAULT_MOBILE_SCOPES),
        )
        return raw

    def _auth(self, raw):
        return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}

    def test_german_aliases_and_status(self):
        raw = self._token()
        status = self.client.get(reverse("api_v1_status"), **self._auth(raw))
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["authenticated"])
        self.assertTrue(status.json()["has_membership"])
        overview = self.client.get(reverse("api_v1_overview"), **self._auth(raw))
        self.assertEqual(overview.status_code, 200)
        self.assertIn("checklists", overview.json()["modules"])
        handovers = self.client.get(reverse("api_v1_uebergaben"), **self._auth(raw))
        self.assertEqual(handovers.status_code, 200)

    def test_create_handover_via_german_alias(self):
        raw = self._token()
        response = self.client.post(
            reverse("api_v1_uebergaben"),
            data=json.dumps({
                "category": HandoverEntry.Category.STATION,
                "priority": HandoverEntry.Priority.NORMAL,
                "title": "Funkgerät laden",
                "details": "Ohne Patientendaten",
            }),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Funkgerät laden")
        self.assertTrue(HandoverEntry.objects.filter(title="Funkgerät laden").exists())

    def test_handover_status_requires_shift_lead(self):
        raw = self._token()
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.NORMAL,
            title="Statuswechsel",
            details="x",
            author=self.user,
        )
        denied = self.client.post(
            reverse("api_v1_uebergabe_status", args=[handover.pk]),
            data=json.dumps({"status": HandoverEntry.Status.IN_PROGRESS}),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(denied.status_code, 403)
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        ok = self.client.post(
            reverse("api_v1_handover_status", args=[handover.pk]),
            data=json.dumps({"status": HandoverEntry.Status.IN_PROGRESS}),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(ok.status_code, 200)
        handover.refresh_from_db()
        self.assertEqual(handover.status, HandoverEntry.Status.IN_PROGRESS)

    def test_calendar_and_coffee_api_respect_modules_and_roles(self):
        raw = self._token()
        cal = self.client.get(reverse("api_v1_kalender"), **self._auth(raw))
        self.assertEqual(cal.status_code, 200)
        self.membership.role = Membership.Role.SHIFT_LEAD
        self.membership.save(update_fields=["role"])
        starts = timezone.now() + timedelta(days=2)
        created = self.client.post(
            reverse("api_v1_kalender"),
            data=json.dumps({
                "title": "Dienstbesprechung",
                "description": "",
                "starts_at": starts.strftime("%Y-%m-%dT%H:%M"),
                "ends_at": (starts + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            }),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(created.status_code, 201)

        self.membership.role = Membership.Role.CASHIER
        self.membership.save(update_fields=["role"])
        coffee = self.client.post(
            reverse("api_v1_kaffeekasse"),
            data=json.dumps({
                "member": self.user.pk,
                "direction": "credit",
                "amount_eur": "5.00",
                "reason": "Einzahlung",
            }),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(coffee.status_code, 201)
        balance = self.client.get(reverse("api_v1_kaffeekasse"), **self._auth(raw))
        self.assertEqual(balance.status_code, 200)
        self.assertGreaterEqual(balance.json()["balance_euros"], 5.0)

        self.station.coffee_enabled = False
        self.station.save(update_fields=["coffee_enabled"])
        missing = self.client.get(reverse("api_v1_kaffeekasse"), **self._auth(raw))
        self.assertEqual(missing.status_code, 404)

    def test_checklists_module_api_and_html(self):
        from .models import Checklist, ChecklistCompletion, ChecklistItem

        raw = self._token()
        disabled = self.client.get(reverse("api_v1_checklisten"), **self._auth(raw))
        self.assertEqual(disabled.status_code, 404)
        html_off = self.client.get(reverse("checklists"))
        self.assertEqual(html_off.status_code, 404)

        self.station.checklists_enabled = True
        self.station.save(update_fields=["checklists_enabled"])
        checklist = Checklist.objects.create(
            station=self.station, title="Fahrzeugcheck", description="Täglich"
        )
        ChecklistItem.objects.create(checklist=checklist, text="Reifen", position=0)
        listed = self.client.get(reverse("api_v1_checklisten"), **self._auth(raw))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["results"][0]["title"], "Fahrzeugcheck")
        self.assertEqual(listed.json()["results"][0]["items"], ["Reifen"])

        done = self.client.post(
            reverse("api_v1_checkliste_erledigt", args=[checklist.pk]),
            data=json.dumps({"note": "Erledigt"}),
            content_type="application/json",
            **self._auth(raw),
        )
        self.assertEqual(done.status_code, 201)
        self.assertEqual(ChecklistCompletion.objects.filter(checklist=checklist).count(), 1)

        html = self.client.get(reverse("checklists"))
        self.assertEqual(html.status_code, 200)
        self.assertContains(html, "Fahrzeugcheck")

    def test_me_and_overview_require_read_me_scope(self):
        raw = self._token(scopes=["read:handovers"])
        me = self.client.get(reverse("api_v1_me"), **self._auth(raw))
        self.assertEqual(me.status_code, 403)
        overview = self.client.get(reverse("api_v1_overview"), **self._auth(raw))
        self.assertEqual(overview.status_code, 403)

    def test_overview_hides_handovers_without_scope(self):
        HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.URGENT,
            title="Geheim",
            details="x",
            author=self.user,
        )
        raw = self._token(scopes=["read:me"])
        overview = self.client.get(reverse("api_v1_overview"), **self._auth(raw))
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["handovers"]["items"], [])
        self.assertEqual(overview.json()["handovers"]["open_count"], 0)

    def test_revoked_token_is_rejected(self):
        from .models import ApiToken

        raw = self._token()
        ApiToken.objects.filter(user=self.user).update(is_active=False)
        response = self.client.get(reverse("api_v1_me"), **self._auth(raw))
        self.assertEqual(response.status_code, 401)

    def test_password_change_revokes_api_tokens(self):
        from .models import ApiToken

        password = "StrongPass-12345"
        self.user.set_password(password)
        self.user.save()
        # Password hash change invalidates the prior force_login session.
        self.client.force_login(self.user)
        raw = self._token()
        self.assertTrue(ApiToken.objects.filter(user=self.user, is_active=True).exists())
        changed = self.client.post(reverse("account_home"), {
            "action": "password",
            "password-old_password": password,
            "password-new_password1": "Completely-New-Pass-99",
            "password-new_password2": "Completely-New-Pass-99",
        })
        self.assertRedirects(changed, reverse("account_home"))
        self.assertFalse(ApiToken.objects.filter(user=self.user, is_active=True).exists())
        denied = self.client.get(reverse("api_v1_me"), **self._auth(raw))
        self.assertEqual(denied.status_code, 401)

    def test_cross_station_handover_returns_json_404(self):
        other = Station.objects.create(name="Andere", slug="andere")
        foreign = HandoverEntry.objects.create(
            station=other,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.NORMAL,
            title="Fremd",
            details="x",
            author=self.user,
        )
        raw = self._token()
        response = self.client.get(
            reverse("api_v1_handover_detail", args=[foreign.pk]),
            **self._auth(raw),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        self.assertFalse(response.json()["ok"])

    def test_checklist_completion_rejects_wrong_station(self):
        from django.core.exceptions import ValidationError

        from .models import Checklist, ChecklistCompletion

        other = Station.objects.create(name="West", slug="west")
        checklist = Checklist.objects.create(station=other, title="Fremdcheck")
        with self.assertRaises(ValidationError):
            ChecklistCompletion.objects.create(
                station=self.station,
                checklist=checklist,
                completed_by=self.user,
            )

    def test_token_exchange_sets_expiry(self):
        password = "StrongPass-12345"
        self.user.set_password(password)
        self.user.save()
        response = self.client.post(
            reverse("api_v1_anmeldung"),
            data=json.dumps({"username": self.user.username, "password": password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["expires_in"], 90 * 24 * 3600)
        self.assertTrue(response.json()["expires_at"])


class CryptoAtRestTests(TestCase):
    def test_aes_gcm_roundtrip_and_legacy_plaintext(self):
        from django.contrib.auth.hashers import identify_hasher

        from .crypto_at_rest import decrypt_secret, encrypt_secret, is_encrypted
        from .mfa import create_pending_device, totp_plaintext, verify_totp

        cipher = encrypt_secret("JBSWY3DPEHPK3PXP")
        self.assertTrue(is_encrypted(cipher))
        self.assertEqual(decrypt_secret(cipher), "JBSWY3DPEHPK3PXP")
        self.assertEqual(decrypt_secret("LEGACYPLAIN"), "LEGACYPLAIN")

        user = User.objects.create_user("crypto@example.org", password="correct-password-1")
        device = create_pending_device(user)
        self.assertTrue(is_encrypted(device.secret))
        plain = totp_plaintext(device)
        self.assertFalse(is_encrypted(plain))
        import pyotp

        self.assertTrue(verify_totp(device, pyotp.TOTP(plain).now()))

        # Argon2id is preferred hasher for new passwords
        user.set_password("another-correct-password-1")
        user.save()
        self.assertEqual(identify_hasher(user.password).algorithm, "argon2")


class MigrationDefaultTests(TestCase):
    def test_feeds_enabled_data_migration_resets_opt_in_default(self):
        from importlib import import_module

        from django.apps import apps

        migration = import_module("core.migrations.0004_disable_feeds_after_module_defaults")
        station = Station.objects.create(
            name="Alt",
            slug="alt-feeds",
            feeds_enabled=True,
        )
        migration.disable_feeds_for_existing_stations(apps, None)
        station.refresh_from_db()
        self.assertFalse(station.feeds_enabled)


class DemoModeTests(TestCase):
    @override_settings(DEMO_MODE=True, DEMO_PASSWORD="Demo-Passwort-12345", MFA_REQUIRED=True)
    def test_load_demo_data_creates_accounts_and_sample_content(self):
        from django.core.management import call_command

        from .demo import DEMO_MARKER, load_demo_data
        from .models import Checklist, CoffeeEntry

        result = load_demo_data()
        self.assertFalse(result.skipped)
        self.assertTrue(User.objects.filter(username="demo-admin").exists())
        self.assertTrue(User.objects.filter(username="demo-mitglied").exists())
        admin = User.objects.get(username="demo-admin")
        self.assertTrue(admin.check_password("Demo-Passwort-12345"))
        membership = Membership.objects.get(user=admin, is_active=True)
        self.assertEqual(membership.role, Membership.Role.ADMIN)
        self.assertTrue(membership.station.checklists_enabled)
        self.assertGreaterEqual(
            HandoverEntry.objects.filter(title__startswith=DEMO_MARKER).count(), 3
        )
        self.assertTrue(CoffeeEntry.objects.filter(reason__startswith=DEMO_MARKER).exists())
        self.assertTrue(Checklist.objects.filter(title__startswith=DEMO_MARKER).exists())

        again = load_demo_data()
        self.assertTrue(again.skipped)
        count = HandoverEntry.objects.filter(title__startswith=DEMO_MARKER).count()
        load_demo_data(reset=True)
        self.assertEqual(
            HandoverEntry.objects.filter(title__startswith=DEMO_MARKER).count(), count
        )

        call_command("load_demo_data")
        landing = self.client.get(reverse("landing"))
        self.assertContains(landing, "Demo-Modus")
        self.assertContains(landing, "demo-admin")
        self.assertContains(landing, "Demo-Passwort-12345")

    def test_load_demo_data_requires_demo_mode_or_force(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("load_demo_data")
        with override_settings(DEBUG=True, DEMO_MODE=False):
            call_command("load_demo_data", force=True)
        self.assertTrue(User.objects.filter(username="demo-admin").exists())
