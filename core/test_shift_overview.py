from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Checklist, HandoverEntry, Membership, Station, StationTask
from core.wachalltag_models import ChecklistSchedule, Defect, StationAsset


class ShiftOverviewTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Rettungswache West",
            slug="wache-west",
            tasks_enabled=True,
            checklists_enabled=True,
        )
        self.user = User.objects.create_user("sanitaeter@example.org", first_name="Alex")
        self.membership = Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        self.client.force_login(self.user)
        self.url = reverse("handover_shift_overview")

    def test_anonymous_redirect(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.headers["Location"])
        self.assertIn("next=", response.headers["Location"])

    def test_no_membership_redirect(self):
        user_no_station = User.objects.create_user("gast@example.org")
        self.client.force_login(user_no_station)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("access"), response.headers["Location"])

    def test_auditor_access_forbidden(self):
        auditor = User.objects.create_user("pruefer@example.org")
        Membership.objects.create(
            user=auditor,
            station=self.station,
            role=Membership.Role.AUDITOR,
        )
        self.client.force_login(auditor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_method_not_allowed(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 405)

    def test_station_isolation(self):
        other_station = Station.objects.create(
            name="Feuerwache Ost",
            slug="feuerwache-ost",
            tasks_enabled=True,
            checklists_enabled=True,
        )
        other_user = User.objects.create_user("feuerwehr@example.org")
        Membership.objects.create(
            user=other_user,
            station=other_station,
            role=Membership.Role.MEMBER,
        )

        # Station 1 data
        HandoverEntry.objects.create(
            station=self.station,
            title="West Übergabe 1",
            details="West Details",
            author=self.user,
            status=HandoverEntry.Status.OPEN,
        )
        StationAsset.objects.create(
            station=self.station,
            asset_id="RTW-01",
            label="RTW West 1",
            status=StationAsset.Status.LIMITED,
            note="Blaulicht defekt",
        )
        Defect.objects.create(
            station=self.station,
            title="Defekt West Trage",
            created_by=self.user,
            status=Defect.Status.OPEN,
        )

        # Other station data
        HandoverEntry.objects.create(
            station=other_station,
            title="GEHEIME Ost Übergabe",
            details="Geheimnis",
            author=other_user,
            status=HandoverEntry.Status.OPEN,
        )
        StationAsset.objects.create(
            station=other_station,
            asset_id="HLF-99",
            label="HLF Ost 99",
            status=StationAsset.Status.OOB,
            note="Pumpe defekt",
        )
        Defect.objects.create(
            station=other_station,
            title="Ost Defekt Atemschutz",
            created_by=other_user,
            status=Defect.Status.OPEN,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Station 1 data must be present
        self.assertContains(response, "West Übergabe 1")
        self.assertContains(response, "RTW West 1")
        self.assertContains(response, "Defekt West Trage")

        # Other station data must NEVER appear
        self.assertNotContains(response, "GEHEIME Ost Übergabe")
        self.assertNotContains(response, "HLF Ost 99")
        self.assertNotContains(response, "Ost Defekt Atemschutz")

    def test_done_handovers_excluded_and_prioritized(self):
        HandoverEntry.objects.create(
            station=self.station,
            title="Erledigte Übergabe",
            details="Bereits erledigt",
            author=self.user,
            status=HandoverEntry.Status.DONE,
        )
        normal = HandoverEntry.objects.create(
            station=self.station,
            title="Normale offene Übergabe",
            details="Normal",
            priority=HandoverEntry.Priority.NORMAL,
            author=self.user,
            status=HandoverEntry.Status.OPEN,
        )
        urgent = HandoverEntry.objects.create(
            station=self.station,
            title="Dringende Übergabe",
            details="Sehr dringend",
            priority=HandoverEntry.Priority.URGENT,
            author=self.user,
            status=HandoverEntry.Status.OPEN,
        )
        important = HandoverEntry.objects.create(
            station=self.station,
            title="Wichtige Übergabe",
            details="Wichtig",
            priority=HandoverEntry.Priority.IMPORTANT,
            author=self.user,
            status=HandoverEntry.Status.OPEN,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        open_handovers = list(response.context["open_handovers"])
        self.assertEqual(len(open_handovers), 3)
        self.assertNotIn("Erledigte Übergabe", [h.title for h in open_handovers])
        self.assertEqual(open_handovers[0].pk, urgent.pk)
        self.assertEqual(open_handovers[1].pk, important.pk)
        self.assertEqual(open_handovers[2].pk, normal.pk)

    def test_assets_filtering(self):
        StationAsset.objects.create(
            station=self.station,
            asset_id="RTW-KLAR",
            label="RTW Klar",
            status=StationAsset.Status.READY,
        )
        limited = StationAsset.objects.create(
            station=self.station,
            asset_id="KTW-LIM",
            label="KTW Eingeschränkt",
            status=StationAsset.Status.LIMITED,
            note="Spiegel beschädigt",
        )
        oob = StationAsset.objects.create(
            station=self.station,
            asset_id="NEF-OOB",
            label="NEF Außer Betrieb",
            status=StationAsset.Status.OOB,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        attention_assets = list(response.context["attention_assets"])
        self.assertEqual(len(attention_assets), 2)
        asset_ids = [a.asset_id for a in attention_assets]
        self.assertIn(limited.asset_id, asset_ids)
        self.assertIn(oob.asset_id, asset_ids)
        self.assertNotIn("RTW-KLAR", asset_ids)
        self.assertContains(response, "KTW Eingeschränkt")
        self.assertContains(response, "NEF Außer Betrieb")

    def test_defects_filtering(self):
        Defect.objects.create(
            station=self.station,
            title="Behobener Mangel",
            created_by=self.user,
            status=Defect.Status.DONE,
        )
        open_defect = Defect.objects.create(
            station=self.station,
            title="Offener Rollstuhlmangel",
            created_by=self.user,
            status=Defect.Status.OPEN,
            priority=Defect.Priority.IMPORTANT,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        open_defects = list(response.context["open_defects"])
        self.assertEqual(len(open_defects), 1)
        self.assertEqual(open_defects[0].pk, open_defect.pk)
        self.assertContains(response, "Offener Rollstuhlmangel")
        self.assertNotContains(response, "Behobener Mangel")

    def test_optional_modules_disabled(self):
        self.station.tasks_enabled = False
        self.station.checklists_enabled = False
        self.station.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["tasks_enabled"])
        self.assertIsNone(response.context["tasks_board"])
        self.assertFalse(response.context["checklists_enabled"])
        self.assertIsNone(response.context["due_checks"])

        self.assertNotContains(response, "Heutige Wachenaufgaben")
        self.assertNotContains(response, "Fällige Checklisten")

    def test_optional_modules_enabled(self):
        self.station.tasks_enabled = True
        self.station.checklists_enabled = True
        self.station.save()

        now = timezone.now()
        cl_due = Checklist.objects.create(
            station=self.station,
            title="Morgendliche Fahrzeugprüfung",
            is_active=True,
        )
        ChecklistSchedule.objects.create(
            station=self.station,
            checklist=cl_due,
            interval=ChecklistSchedule.Interval.DAILY,
            due_next=now - timedelta(hours=1),
        )

        cl_future = Checklist.objects.create(
            station=self.station,
            title="Monatsprüfung Desinfektor",
            is_active=True,
        )
        ChecklistSchedule.objects.create(
            station=self.station,
            checklist=cl_future,
            interval=ChecklistSchedule.Interval.MONTHLY,
            due_next=now + timedelta(days=10),
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["tasks_enabled"])
        self.assertIsNotNone(response.context["tasks_board"])
        self.assertTrue(response.context["checklists_enabled"])

        due_checks = list(response.context["due_checks"])
        self.assertEqual(len(due_checks), 1)
        self.assertEqual(due_checks[0].checklist_id, cl_due.id)
        self.assertContains(response, "Morgendliche Fahrzeugprüfung")
        self.assertNotContains(response, "Monatsprüfung Desinfektor")
        self.assertContains(response, "Heutige Wachenaufgaben")

    def test_query_count_is_bounded(self):
        # Warm up session and ensure default station tasks are created
        self.client.get(self.url)

        # Create multiple items of each type
        for i in range(10):
            HandoverEntry.objects.create(
                station=self.station,
                title=f"Übergabe {i}",
                details=f"Details {i}",
                author=self.user,
                status=HandoverEntry.Status.OPEN,
            )
            StationAsset.objects.create(
                station=self.station,
                asset_id=f"A-{i}",
                label=f"Asset {i}",
                status=StationAsset.Status.LIMITED,
            )
            Defect.objects.create(
                station=self.station,
                title=f"Mangel {i}",
                created_by=self.user,
                status=Defect.Status.OPEN,
            )

        # Query count should stay minimal and fixed (exactly 15 queries regardless of item count)
        with self.assertNumQueries(15):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

    def test_link_in_handover_list(self):
        response = self.client.get(reverse("handover_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
        self.assertContains(response, "Schichtüberblick")

    def test_ui_disclaimer_and_timestamp(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schichtüberblick")
        self.assertContains(response, "Stand:")
        self.assertContains(response, "Stationszeit")
        self.assertContains(response, "Keine Patienten-, Einsatz- oder Personaldaten")
        self.assertContains(response, "kein rechtsverbindliches Übergabeprotokoll")
