import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

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
    Checklist,
    ChecklistCompletion,
    ChecklistItem,
    CoffeeEntry,
    FeedItem,
    FeedSource,
    HandoverEntry,
    HandoverRevision,
    Membership,
    Station,
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


class SecurityAndAccessTests(PilotTestCase):
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


class ClientApiTests(PilotTestCase):
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

    def test_status_reports_membership_for_signed_in_member(self):
        response = self.client.get(reverse("api:status"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["authenticated"])
        self.assertTrue(data["has_membership"])
        self.assertEqual(data["station"], self.station.name)
        self.assertEqual(data["role"], Membership.Role.MEMBER)
        self.assertIn("api_version", data)

    def test_status_is_available_without_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("api:status"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["authenticated"])
        self.assertFalse(data["has_membership"])
        self.assertNotIn("station", data)

    def test_overview_returns_prioritized_station_summary(self):
        self.create_handover("Normal", HandoverEntry.Priority.NORMAL)
        urgent = self.create_handover("Dringend", HandoverEntry.Priority.URGENT)
        self.create_handover(
            "Erledigt", HandoverEntry.Priority.URGENT, HandoverEntry.Status.DONE
        )
        CoffeeEntry.objects.create(
            station=self.station,
            member=self.user,
            amount_cents=500,
            reason="Einzahlung",
            created_by=self.user,
        )
        response = self.client.get(reverse("api:overview"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["station"]["slug"], self.station.slug)
        self.assertEqual(data["role"], Membership.Role.MEMBER)
        self.assertEqual(data["handovers"]["open_count"], 2)
        self.assertEqual(data["handovers"]["urgent_count"], 1)
        self.assertEqual(data["handovers"]["items"][0]["id"], urgent.pk)
        self.assertEqual(data["coffee"]["own_balance_euros"], 5.0)
        self.assertFalse(data["coffee"]["can_book"])
        self.assertNotIn("total_balance_euros", data["coffee"])

    def test_overview_cashier_sees_total_balance(self):
        self.membership.role = Membership.Role.CASHIER
        self.membership.save(update_fields=["role"])
        other = User.objects.create_user("colleague@example.org")
        CoffeeEntry.objects.create(
            station=self.station,
            member=other,
            amount_cents=700,
            reason="Einzahlung",
            created_by=self.user,
        )
        response = self.client.get(reverse("api:overview"))
        data = response.json()
        self.assertTrue(data["coffee"]["can_book"])
        self.assertEqual(data["coffee"]["own_balance_euros"], 0.0)
        self.assertEqual(data["coffee"]["total_balance_euros"], 7.0)

    def test_overview_hides_disabled_modules(self):
        self.station.calendar_enabled = False
        self.station.coffee_enabled = False
        self.station.save(update_fields=["calendar_enabled", "coffee_enabled"])
        response = self.client.get(reverse("api:overview"))
        data = response.json()
        self.assertNotIn("events", data)
        self.assertNotIn("coffee", data)
        self.assertFalse(data["modules"]["calendar"])

    def test_overview_is_station_scoped(self):
        other_station = Station.objects.create(name="Andere", slug="andere")
        HandoverEntry.objects.create(
            station=other_station,
            category=HandoverEntry.Category.TASK,
            title="Fremd",
            details="Stationsfremd",
            author=self.user,
        )
        response = self.client.get(reverse("api:overview"))
        data = response.json()
        self.assertEqual(data["handovers"]["open_count"], 0)

    def test_overview_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("api:overview"))
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_overview_forbidden_for_auditor(self):
        self.membership.role = Membership.Role.AUDITOR
        self.membership.save(update_fields=["role"])
        response = self.client.get(reverse("api:overview"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())

    def test_overview_rejects_non_get_methods(self):
        response = self.client.post(reverse("api:overview"))
        self.assertEqual(response.status_code, 405)

    def test_handover_list_scopes_active_dringend_and_archiv(self):
        normal = self.create_handover("Normal", HandoverEntry.Priority.NORMAL)
        urgent = self.create_handover("Dringend", HandoverEntry.Priority.URGENT)
        done = self.create_handover(
            "Erledigt", HandoverEntry.Priority.URGENT, HandoverEntry.Status.DONE
        )
        active = self.client.get(reverse("api:handover_list")).json()
        self.assertEqual([item["id"] for item in active["results"]], [urgent.pk, normal.pk])
        urgent_only = self.client.get(
            reverse("api:handover_list"), {"ansicht": "dringend"}
        ).json()
        self.assertEqual([item["id"] for item in urgent_only["results"]], [urgent.pk])
        archive = self.client.get(
            reverse("api:handover_list"), {"ansicht": "archiv"}
        ).json()
        self.assertEqual([item["id"] for item in archive["results"]], [done.pk])

    def test_handover_detail_includes_body_and_is_station_scoped(self):
        handover = self.create_handover("Detail", HandoverEntry.Priority.IMPORTANT)
        data = self.client.get(
            reverse("api:handover_detail", args=[handover.pk])
        ).json()
        self.assertEqual(data["id"], handover.pk)
        self.assertEqual(data["details"], "Testinhalt")
        self.assertIn("revisions", data)

        other = Station.objects.create(name="Andere", slug="andere2")
        foreign = HandoverEntry.objects.create(
            station=other,
            category=HandoverEntry.Category.TASK,
            title="Fremd",
            details="x",
            author=self.user,
        )
        response = self.client.get(reverse("api:handover_detail", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)

    def test_calendar_endpoint_respects_module_switch(self):
        CalendarEvent.objects.create(
            station=self.station,
            title="Geraetepruefung",
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=2),
            created_by=self.user,
        )
        data = self.client.get(reverse("api:calendar")).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["title"], "Geraetepruefung")

        self.station.calendar_enabled = False
        self.station.save(update_fields=["calendar_enabled"])
        response = self.client.get(reverse("api:calendar"))
        self.assertEqual(response.status_code, 404)

    def test_coffee_endpoint_scopes_entries_by_role(self):
        other = User.objects.create_user("colleague2@example.org")
        CoffeeEntry.objects.create(
            station=self.station, member=self.user, amount_cents=500,
            reason="Eigen", created_by=self.user,
        )
        CoffeeEntry.objects.create(
            station=self.station, member=other, amount_cents=300,
            reason="Fremd", created_by=self.user,
        )
        member_view = self.client.get(reverse("api:coffee")).json()
        self.assertEqual(member_view["count"], 1)
        self.assertEqual(member_view["balances"]["own_balance_euros"], 5.0)
        self.assertFalse(member_view["balances"]["can_book"])

        self.membership.role = Membership.Role.CASHIER
        self.membership.save(update_fields=["role"])
        cashier_view = self.client.get(reverse("api:coffee")).json()
        self.assertEqual(cashier_view["count"], 2)
        self.assertEqual(cashier_view["balances"]["total_balance_euros"], 8.0)


class ChecklistModuleTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.station.checklists_enabled = True
        self.station.save(update_fields=["checklists_enabled"])
        self.checklist = Checklist.objects.create(
            station=self.station, title="Täglicher RTW-Check"
        )
        ChecklistItem.objects.create(checklist=self.checklist, text="Sauerstoff prüfen", position=1)
        ChecklistItem.objects.create(checklist=self.checklist, text="AED prüfen", position=2)

    def test_module_toggle_hides_checklists(self):
        self.assertEqual(self.client.get(reverse("checklists")).status_code, 200)
        self.station.checklists_enabled = False
        self.station.save(update_fields=["checklists_enabled"])
        self.assertEqual(self.client.get(reverse("checklists")).status_code, 404)

    def test_more_page_lists_checklists_only_when_enabled(self):
        self.assertContains(self.client.get(reverse("more")), "Checklisten")
        self.station.checklists_enabled = False
        self.station.save(update_fields=["checklists_enabled"])
        self.assertNotContains(self.client.get(reverse("more")), "Checklisten")

    def test_completion_is_recorded_with_audit(self):
        response = self.client.post(
            reverse("checklist_complete", args=[self.checklist.pk]),
            {"note": "Alles in Ordnung"},
        )
        self.assertRedirects(response, reverse("checklists"))
        completion = ChecklistCompletion.objects.get()
        self.assertEqual(completion.checklist, self.checklist)
        self.assertEqual(completion.completed_by, self.user)
        self.assertTrue(AuditEvent.objects.filter(action="checklist.completed").exists())

    def test_completion_is_immutable(self):
        completion = ChecklistCompletion.objects.create(
            station=self.station, checklist=self.checklist, completed_by=self.user
        )
        completion.note = "geändert"
        with self.assertRaises(ValidationError):
            completion.save()
        with self.assertRaises(ValidationError):
            completion.delete()

    def test_completion_is_station_scoped(self):
        other = Station.objects.create(name="Andere", slug="andere-cl")
        foreign = Checklist.objects.create(station=other, title="Fremd")
        response = self.client.post(
            reverse("checklist_complete", args=[foreign.pk]), {}
        )
        self.assertEqual(response.status_code, 404)


class ClientApiTokenTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Tokenwache", slug="tokenwache")
        self.user = User.objects.create_user(
            "token@example.org", password="a-strong-test-password"
        )
        Membership.objects.create(
            user=self.user, station=self.station, role=Membership.Role.MEMBER
        )

    def login(self, password="a-strong-test-password"):
        return self.client.post(
            reverse("api:login"),
            data=json.dumps({"username": "token@example.org", "password": password}),
            content_type="application/json",
        )

    def test_valid_credentials_return_a_bearer_token(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("token", body)
        self.assertTrue(body["has_membership"])
        self.assertEqual(body["station"], "Tokenwache")

    def test_invalid_credentials_are_rejected(self):
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("token", response.json())

    def test_missing_fields_return_bad_request(self):
        response = self.client.post(
            reverse("api:login"),
            data=json.dumps({"username": "token@example.org"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_bearer_token_authenticates_protected_endpoint(self):
        token = self.login().json()["token"]
        response = self.client.get(
            reverse("api:overview"), HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["station"]["slug"], "tokenwache")

    def test_status_reports_authentication_via_token(self):
        token = self.login().json()["token"]
        data = self.client.get(
            reverse("api:status"), HTTP_AUTHORIZATION=f"Bearer {token}"
        ).json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["role"], Membership.Role.MEMBER)

    def test_tampered_token_is_rejected(self):
        response = self.client.get(
            reverse("api:overview"), HTTP_AUTHORIZATION="Bearer not-a-valid-token"
        )
        self.assertEqual(response.status_code, 401)


class ClientApiWriteTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Schreibwache", slug="schreibwache")
        self.user = User.objects.create_user(
            "writer@example.org", password="pw-strong-12345"
        )
        self.membership = Membership.objects.create(
            user=self.user, station=self.station, role=Membership.Role.ADMIN
        )

    def token(self, role=None):
        if role is not None:
            self.membership.role = role
            self.membership.save(update_fields=["role"])
        response = self.client.post(
            reverse("api:login"),
            data=json.dumps(
                {"username": "writer@example.org", "password": "pw-strong-12345"}
            ),
            content_type="application/json",
        )
        return response.json()["token"]

    def post(self, url, body, token):
        return self.client.post(
            url,
            data=json.dumps(body),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def make_handover(self):
        return HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.STATION,
            priority=HandoverEntry.Priority.NORMAL,
            title="Bestehend",
            details="Inhalt",
            author=self.user,
        )

    def test_member_creates_versioned_handover_with_audit(self):
        token = self.token(role=Membership.Role.MEMBER)
        response = self.post(
            reverse("api:handover_list"),
            {
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.IMPORTANT,
                "title": "Material nachbestellen",
                "details": "Verbrauchsmaterial pruefen.",
            },
            token,
        )
        self.assertEqual(response.status_code, 201)
        handover = HandoverEntry.objects.get(title="Material nachbestellen")
        self.assertEqual(handover.station, self.station)
        self.assertEqual(handover.revisions.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="handover.created").exists())

    def test_create_handover_validates_input(self):
        token = self.token(role=Membership.Role.MEMBER)
        response = self.post(
            reverse("api:handover_list"),
            {"category": HandoverEntry.Category.TASK, "title": "", "details": ""},
            token,
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("fields", response.json())

    def test_writes_require_a_bearer_token(self):
        # A session cookie alone must not authorise writes.
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("api:handover_list"),
            data=json.dumps({
                "category": HandoverEntry.Category.TASK,
                "priority": HandoverEntry.Priority.NORMAL,
                "title": "Ohne Token",
                "details": "Sollte scheitern.",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(HandoverEntry.objects.filter(title="Ohne Token").exists())

    def test_status_change_requires_shift_lead_or_admin(self):
        handover = self.make_handover()
        member_token = self.token(role=Membership.Role.MEMBER)
        denied = self.post(
            reverse("api:handover_status", args=[handover.pk]),
            {"status": HandoverEntry.Status.DONE},
            member_token,
        )
        self.assertEqual(denied.status_code, 403)
        handover.refresh_from_db()
        self.assertEqual(handover.status, HandoverEntry.Status.OPEN)

        admin_token = self.token(role=Membership.Role.ADMIN)
        allowed = self.post(
            reverse("api:handover_status", args=[handover.pk]),
            {"status": HandoverEntry.Status.DONE},
            admin_token,
        )
        self.assertEqual(allowed.status_code, 200)
        handover.refresh_from_db()
        self.assertEqual(handover.status, HandoverEntry.Status.DONE)
        self.assertEqual(handover.version, 2)
        self.assertIsNotNone(handover.completed_at)
        self.assertTrue(
            AuditEvent.objects.filter(action="handover.status_changed").exists()
        )

    def test_status_change_is_station_scoped(self):
        other = Station.objects.create(name="Fremd", slug="fremd")
        foreign = HandoverEntry.objects.create(
            station=other,
            category=HandoverEntry.Category.TASK,
            title="Fremd",
            details="x",
            author=self.user,
        )
        token = self.token(role=Membership.Role.ADMIN)
        response = self.post(
            reverse("api:handover_status", args=[foreign.pk]),
            {"status": HandoverEntry.Status.DONE},
            token,
        )
        self.assertEqual(response.status_code, 404)

    def test_shift_lead_creates_calendar_event_with_audit(self):
        token = self.token(role=Membership.Role.SHIFT_LEAD)
        response = self.post(
            reverse("api:calendar"),
            {
                "title": "Geräteprüfung",
                "description": "Jährliche Prüfung",
                "starts_at": "2026-08-01 09:00:00",
                "ends_at": "2026-08-01 11:00:00",
            },
            token,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CalendarEvent.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="calendar.created").exists())

    def test_calendar_create_requires_shift_lead_or_admin(self):
        token = self.token(role=Membership.Role.MEMBER)
        response = self.post(
            reverse("api:calendar"),
            {
                "title": "Nicht erlaubt",
                "starts_at": "2026-08-01 09:00:00",
                "ends_at": "2026-08-01 11:00:00",
            },
            token,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CalendarEvent.objects.count(), 0)

    def test_calendar_create_rejects_end_before_start(self):
        token = self.token(role=Membership.Role.ADMIN)
        response = self.post(
            reverse("api:calendar"),
            {
                "title": "Verdreht",
                "starts_at": "2026-08-01 11:00:00",
                "ends_at": "2026-08-01 09:00:00",
            },
            token,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(CalendarEvent.objects.count(), 0)

    def test_checklist_api_lists_and_completes(self):
        self.station.checklists_enabled = True
        self.station.save(update_fields=["checklists_enabled"])
        checklist = Checklist.objects.create(station=self.station, title="RTW-Check")
        ChecklistItem.objects.create(checklist=checklist, text="Sauerstoff", position=1)
        token = self.token(role=Membership.Role.MEMBER)
        listing = self.client.get(
            reverse("api:checklists"), HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(listing.status_code, 200)
        data = listing.json()
        self.assertEqual(data["results"][0]["title"], "RTW-Check")
        self.assertEqual(data["results"][0]["items"], ["Sauerstoff"])
        done = self.post(
            reverse("api:checklist_complete", args=[checklist.pk]),
            {"note": "ok"},
            token,
        )
        self.assertEqual(done.status_code, 201)
        self.assertEqual(ChecklistCompletion.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="checklist.completed").exists())

    def test_checklist_api_hidden_when_module_disabled(self):
        token = self.token(role=Membership.Role.MEMBER)
        response = self.client.get(
            reverse("api:checklists"), HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 404)

    def test_coffee_booking_requires_cashier_or_admin(self):
        member_token = self.token(role=Membership.Role.MEMBER)
        denied = self.post(
            reverse("api:coffee"),
            {
                "member": self.user.pk,
                "direction": "credit",
                "amount_eur": "3.50",
                "reason": "Einzahlung",
            },
            member_token,
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(CoffeeEntry.objects.count(), 0)

        cashier_token = self.token(role=Membership.Role.CASHIER)
        allowed = self.post(
            reverse("api:coffee"),
            {
                "member": self.user.pk,
                "direction": "credit",
                "amount_eur": "3.50",
                "reason": "Einzahlung",
            },
            cashier_token,
        )
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(CoffeeEntry.objects.get().amount_cents, 350)
        self.assertTrue(
            AuditEvent.objects.filter(action="coffee.entry_created").exists()
        )


class TeamAndAuditTests(PilotTestCase):
    def setUp(self):
        super().setUp()
        self.membership.role = Membership.Role.ADMIN
        self.membership.save(update_fields=["role"])

    def test_station_admin_assigns_pending_tailscale_user(self):
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
