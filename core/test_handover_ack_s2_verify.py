"""Unabhaengige S2-Verifikation (revisionsgebundene Uebergabequittierung).

Dieses Modul wurde vom ausfuehrenden Agenten als Gegenpruefung zum AGY-Bericht
geschrieben, unabhaengig von ``core/test_handover_ack_revision.py``. Es prueft
das reale End-to-End-Verhalten ueber die HTTP-Schicht, die Web-Route, den
Auditdatensatz und das Migrations-Legacy-Verhalten (keine erfundene Revision).
"""

import json
import re
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from core.api.views import hash_api_token
from core.models import ApiToken, AuditEvent, HandoverEntry, Membership, Station
from core.wachalltag_models import HandoverAck
from core.services import update_handover_content

MIGRATION_PATH = (
    Path(__file__).resolve().parent / "migrations" / "0027_handover_ack_version.py"
)


class MigrationLegacyContractTests(TransactionTestCase):
    """Die Migration darf fuer Altbestand keine Revision erfinden."""

    def test_migration_adds_nullable_version_without_backfill(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("core", "0026_station_organization_profile")])

        def cleanup_migration():
            executor.loader.build_graph()
            executor.migrate([("core", "0027_handover_ack_version")])

        self.addCleanup(cleanup_migration)

        station = Station.objects.create(name="Legacy Wache", slug="legacy-wache")
        user = User.objects.create_user(username="legacy_user", password="legacy")
        handover = HandoverEntry.objects.create(
            station=station,
            category=HandoverEntry.Category.MATERIAL,
            title="Legacy",
            details="Leg",
            author=user,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO core_handoverack (station_id, handover_id, user_id, created_at) "
                "VALUES (%s, %s, %s, '2020-01-01')",
                [station.id, handover.id, user.id],
            )
        executor.loader.build_graph()
        executor.migrate([("core", "0027_handover_ack_version")])
        legacy_ack = HandoverAck.objects.filter(
            handover_id=handover.id, version__isnull=True
        ).first()
        self.assertIsNotNone(legacy_ack)
        self.assertIsNone(legacy_ack.version)
        HandoverAck.objects.create(
            station_id=station.id, handover_id=handover.id, user_id=user.id, version=1
        )
        self.assertEqual(HandoverAck.objects.filter(handover_id=handover.id).count(), 2)


class RevisionBoundAckEndToEndTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Verif Wache", slug="verif-wache")
        self.user = User.objects.create_user(
            username="verif-user", password="test-password"
        )
        Membership.objects.create(
            user=self.user, station=self.station, role=Membership.Role.MEMBER
        )
        self.handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.MATERIAL,
            priority=HandoverEntry.Priority.NORMAL,
            status=HandoverEntry.Status.OPEN,
            title="Verif-Uebergabe",
            details="Alt",
            author=self.user,
        )
        raw = "wb_verif_token_1234567890"
        ApiToken.objects.create(
            user=self.user,
            label="Verif",
            token_prefix=raw[:11],
            token_hash=hash_api_token(raw),
            scopes=["read:me", "read:handovers", "write:handovers"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {raw}"}

    def _post_ack(self, version):
        return self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data=json.dumps({"version": version}),
            content_type="application/json",
            **self.auth,
        )

    def _bump(self):
        update_handover_content(
            self.handover,
            {
                "title": "Verif-Uebergabe neu",
                "details": "Neu",
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.NORMAL,
            },
            Membership.objects.get(user=self.user, station=self.station),
        )
        self.handover.refresh_from_db()

    def test_ack_is_bound_to_read_revision_and_preserved_after_change(self):
        first = self._post_ack(1)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["version"], 1)
        old = HandoverAck.objects.get(handover=self.handover, user=self.user)
        old_created = old.created_at

        # Idempotent fuer dieselbe Revision.
        again = self._post_ack(1)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(HandoverAck.objects.filter(handover=self.handover).count(), 1)

        self._bump()
        self.assertEqual(self.handover.version, 2)

        # Alte (gelesene) Revision ist jetzt veraltet -> fail-closed, keine Zeile.
        stale = self._post_ack(1)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["error"]["code"], "conflict")
        self.assertEqual(HandoverAck.objects.filter(handover=self.handover).count(), 1)

        # Neue Revision separat quittieren -> zweite Zeile, alte bleibt unveraendert.
        new = self._post_ack(2)
        self.assertEqual(new.status_code, 201)
        self.assertEqual(HandoverAck.objects.filter(handover=self.handover).count(), 2)
        old.refresh_from_db()
        self.assertEqual(old.version, 1)
        self.assertEqual(old.created_at, old_created)

    def test_acks_listing_exposes_revision_and_null_for_legacy(self):
        HandoverAck.objects.create(
            station=self.station, handover=self.handover, user=self.user, version=None
        )
        self._post_ack(1)
        listing = self.client.get(
            f"/api/v1/handovers/{self.handover.pk}/acks/", **self.auth
        )
        self.assertEqual(listing.status_code, 200)
        versions = sorted(
            (row["version"] if row["version"] is not None else -1)
            for row in listing.json()["results"]
        )
        self.assertEqual(versions, [-1, 1])

    def test_textbook_race_simulation_stale_version_no_side_effect(self):
        # "Gelesene Revision != aktuelle Revision" fail-closed ohne Nebenwirkung.
        self._bump()
        before = HandoverAck.objects.count()
        response = self._post_ack(1)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(HandoverAck.objects.count(), before)
        self.assertFalse(
            AuditEvent.objects.filter(action="handover.acknowledged").exists()
        )

    def test_audit_has_only_structured_fields(self):
        self._post_ack(1)
        event = AuditEvent.objects.get(action="handover.acknowledged")
        self.assertEqual(set(event.metadata), {"version"})
        self.assertEqual(event.metadata["version"], 1)
        self.assertEqual(event.object_type, "HandoverEntry")

    def test_web_post_requires_csrf_and_acks(self):
        url = reverse("handover_ack", args=[self.handover.pk])
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)

        # Ohne CSRF-Token abgelehnt.
        blocked = c.post(url, {"version": 1})
        self.assertEqual(blocked.status_code, 403)
        self.assertFalse(HandoverAck.objects.exists())

        detail = c.get(reverse("handover_detail", args=[self.handover.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertIn("quittieren", detail.content.decode())
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', detail.content.decode()
        ).group(1)
        ok = c.post(url, {"csrfmiddlewaretoken": token, "version": 1})
        self.assertRedirects(ok, reverse("handover_detail", args=[self.handover.pk]))
        self.assertEqual(HandoverAck.objects.filter(handover=self.handover).count(), 1)

        # Stale Web-POST erzeugt keine weitere Zeile.
        stale = c.post(url, {"csrfmiddlewaretoken": token, "version": 999})
        self.assertEqual(stale.status_code, 302)
        self.assertEqual(HandoverAck.objects.filter(handover=self.handover).count(), 1)

    def test_auditor_cannot_ack_via_api(self):
        auditor = User.objects.create_user(
            username="verif-auditor", password="test-password"
        )
        Membership.objects.create(
            user=auditor, station=self.station, role=Membership.Role.AUDITOR
        )
        raw = "wb_verif_auditor_1234567890"
        ApiToken.objects.create(
            user=auditor,
            label="Auditor",
            token_prefix=raw[:11],
            token_hash=hash_api_token(raw),
            scopes=["read:me", "read:handovers", "write:handovers"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data=json.dumps({"version": 1}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {raw}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(HandoverAck.objects.exists())
