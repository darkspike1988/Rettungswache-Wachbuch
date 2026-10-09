import base64
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.api.views import hash_api_token
from core.errors import ERROR_CODE_CONFLICT
from core.models import ApiToken, AuditEvent, HandoverEntry, Membership, Station
from core.services import (
    InvalidHandoverRevision,
    StaleHandoverRevision,
    acknowledge_handover,
    update_handover_content,
)
from core.wachalltag_models import HandoverAck


class HandoverAckRevisionTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Wache A", slug="wache-a")
        self.other_station = Station.objects.create(name="Wache B", slug="wache-b")

        self.user = User.objects.create_user(username="user", password="test-password")
        self.membership = Membership.objects.create(
            user=self.user, station=self.station, role=Membership.Role.MEMBER
        )

        self.auditor = User.objects.create_user(
            username="auditor", password="test-password"
        )
        self.auditor_membership = Membership.objects.create(
            user=self.auditor, station=self.station, role=Membership.Role.AUDITOR
        )

        self.other_user = User.objects.create_user(
            username="other", password="test-password"
        )
        self.other_membership = Membership.objects.create(
            user=self.other_user,
            station=self.other_station,
            role=Membership.Role.MEMBER,
        )

        self.handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.MATERIAL,
            priority=HandoverEntry.Priority.NORMAL,
            status=HandoverEntry.Status.OPEN,
            title="Übergabe",
            details="Test",
            author=self.user,
        )

        self.client = Client()
        self.client.force_login(self.user)

        self.raw_token = "wb_test_token_1234567890"
        ApiToken.objects.create(
            user=self.user,
            label="Tests",
            token_prefix=self.raw_token[:11],
            token_hash=hash_api_token(self.raw_token),
            scopes=["read:me", "read:handovers", "write:handovers"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {self.raw_token}"}

    def test_legacy_migration_allows_null_version_and_prevents_duplicates(self):
        # Legacy/Migration allows None
        ack = HandoverAck.objects.create(
            station=self.station, handover=self.handover, user=self.user, version=None
        )
        self.assertIsNone(ack.version)

        # But duplicates for a given version raise IntegrityError
        HandoverAck.objects.create(
            station=self.station, handover=self.handover, user=self.user, version=1
        )
        with self.assertRaises(IntegrityError):
            HandoverAck.objects.create(
                station=self.station, handover=self.handover, user=self.user, version=1
            )

    def test_idempotence(self):
        ack1, created1 = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )
        self.assertTrue(created1)
        self.assertEqual(HandoverAck.objects.count(), 1)

        ack2, created2 = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )
        self.assertFalse(created2)
        self.assertEqual(HandoverAck.objects.count(), 1)

    def test_acknowledge_after_change(self):
        ack1, _ = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )

        update_handover_content(
            self.handover,
            {
                "title": "Neu",
                "details": "Neu",
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.NORMAL,
            },
            self.membership,
        )
        self.handover.refresh_from_db()
        self.assertEqual(self.handover.version, 2)

        ack2, _ = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )

        self.assertEqual(HandoverAck.objects.count(), 2)
        self.assertEqual(ack1.version, 1)
        self.assertEqual(ack2.version, 2)

    def test_race_fail_closed(self):
        update_handover_content(
            self.handover,
            {
                "title": "Neu",
                "details": "Neu",
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.NORMAL,
            },
            self.membership,
        )
        self.handover.refresh_from_db()
        self.assertEqual(self.handover.version, 2)

        with self.assertRaises(StaleHandoverRevision):
            acknowledge_handover(self.handover, self.membership, read_version=1)

        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_cross_station(self):
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            acknowledge_handover(self.handover, self.other_membership, read_version=1)
        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_role_auditor(self):
        self.client.force_login(self.auditor)
        response = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]),
            {"version": self.handover.version},
        )
        self.assertEqual(response.status_code, 403)

    def test_audit_logs(self):
        ack, created = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )
        log = AuditEvent.objects.filter(action="handover.acknowledged").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata["version"], self.handover.version)
        self.assertNotIn("title", log.metadata)
        self.assertNotIn("details", log.metadata)

    def test_reports_unacknowledged_active_handovers_revision_aware(self):
        response = self.client.get("/api/v1/reports/", **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unacknowledged_active_handovers"], 1)

        acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )

        response2 = self.client.get("/api/v1/reports/", **self.auth)
        self.assertEqual(response2.json()["unacknowledged_active_handovers"], 0)

        update_handover_content(
            self.handover,
            {
                "title": "Neu",
                "details": "Neu",
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.NORMAL,
            },
            self.membership,
        )

        response3 = self.client.get("/api/v1/reports/", **self.auth)
        self.assertEqual(response3.json()["unacknowledged_active_handovers"], 1)

    def test_legacy_null_ack_does_not_satisfy_current_version(self):
        HandoverAck.objects.create(
            station=self.station, handover=self.handover, user=self.user, version=None
        )
        report = self.client.get("/api/v1/reports/", **self.auth)
        self.assertEqual(report.json()["unacknowledged_active_handovers"], 1)

        ack, created = acknowledge_handover(
            self.handover, self.membership, read_version=self.handover.version
        )
        self.assertTrue(created)
        self.assertEqual(
            HandoverAck.objects.filter(handover=self.handover, user=self.user).count(),
            2,
        )
        report2 = self.client.get("/api/v1/reports/", **self.auth)
        self.assertEqual(report2.json()["unacknowledged_active_handovers"], 0)

    def test_api_ack_without_version_is_rejected(self):
        first = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data="{}",
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(first.status_code, 422)
        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_api_malformed_version_is_rejected(self):
        response = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data=json.dumps({"version": "abc"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_invalid_versions_matrix_api_service_web(self):
        # Service: keiner dieser Werte darf eine Quittung erzeugen (kein Fallback
        # auf die aktuelle Revision, keine Nebenwirkung).
        for bad in (None, True, False, 5.0, "abc", "", 0, -1):
            with self.assertRaises(
                InvalidHandoverRevision, msg=f"Service akzeptierte {bad!r}"
            ):
                acknowledge_handover(self.handover, self.membership, read_version=bad)
        self.assertEqual(HandoverAck.objects.count(), 0)
        self.assertEqual(
            AuditEvent.objects.filter(action="handover.acknowledged").count(), 0
        )

        # API
        invalid_payloads = [
            "",  # fehlender Body
            json.dumps({"version": None}),
            json.dumps({"version": True}),
            json.dumps({"version": "5"}),
            json.dumps({"version": 5.0}),
            json.dumps({"version": 0}),
            json.dumps({"version": -1}),
        ]
        for payload in invalid_payloads:
            resp = self.client.post(
                f"/api/v1/handovers/{self.handover.pk}/ack/",
                data=payload,
                content_type="application/json" if payload else "text/plain",
                **self.auth,
            )
            self.assertEqual(resp.status_code, 422, f"Failed for payload: {payload}")
            self.assertEqual(HandoverAck.objects.count(), 0)
            self.assertEqual(
                AuditEvent.objects.filter(action="handover.acknowledged").count(), 0
            )

        # Web ohne Version -> kein Ack, kein Audit
        resp_web1 = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]), {}
        )
        self.assertRedirects(
            resp_web1, reverse("handover_detail", args=[self.handover.pk])
        )
        self.assertEqual(HandoverAck.objects.count(), 0)
        self.assertEqual(
            AuditEvent.objects.filter(action="handover.acknowledged").count(), 0
        )

        # Web mit veralteter (nicht gelesener) Version -> kein Ack, kein Audit
        resp_web2 = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]), {"version": 999}
        )
        self.assertRedirects(
            resp_web2, reverse("handover_detail", args=[self.handover.pk])
        )
        self.assertEqual(HandoverAck.objects.count(), 0)
        self.assertEqual(
            AuditEvent.objects.filter(action="handover.acknowledged").count(), 0
        )

    def test_api_cross_station_returns_404(self):
        other_station = Station.objects.create(name="Wache C", slug="wache-c")
        outsider = User.objects.create_user(
            username="outsider", password="test-password"
        )
        Membership.objects.create(
            user=outsider, station=other_station, role=Membership.Role.MEMBER
        )
        raw = "wb_outsider_token_1234567890"
        ApiToken.objects.create(
            user=outsider,
            label="Outsider",
            token_prefix=raw[:11],
            token_hash=hash_api_token(raw),
            scopes=["read:me", "read:handovers", "write:handovers"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data=json.dumps({"version": self.handover.version}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {raw}",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_web_cross_station_returns_404(self):
        other_station = Station.objects.create(name="Wache D", slug="wache-d")
        outsider = User.objects.create_user(
            username="outsider2", password="test-password"
        )
        Membership.objects.create(
            user=outsider, station=other_station, role=Membership.Role.MEMBER
        )
        c = Client()
        c.force_login(outsider)
        response = c.post(
            reverse("handover_ack", args=[self.handover.pk]), {"version": 1}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(HandoverAck.objects.count(), 0)

    def test_web_view(self):
        response_get = self.client.get(
            reverse("handover_detail", args=[self.handover.pk])
        )
        self.assertEqual(response_get.status_code, 200)
        self.assertContains(response_get, 'name="version"')

        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        response_csrf = c.post(
            reverse("handover_ack", args=[self.handover.pk]),
            {"version": self.handover.version},
        )
        self.assertEqual(response_csrf.status_code, 403)

        response_post = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]),
            {"version": self.handover.version},
        )
        self.assertRedirects(
            response_post, reverse("handover_detail", args=[self.handover.pk])
        )
        self.assertEqual(HandoverAck.objects.count(), 1)

        response_post_stale = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]), {"version": 999}
        )
        self.assertRedirects(
            response_post_stale, reverse("handover_detail", args=[self.handover.pk])
        )
        self.assertEqual(HandoverAck.objects.count(), 1)

        response_post_idempotent = self.client.post(
            reverse("handover_ack", args=[self.handover.pk]),
            {"version": self.handover.version},
        )
        self.assertRedirects(
            response_post_idempotent,
            reverse("handover_detail", args=[self.handover.pk]),
        )
        self.assertEqual(HandoverAck.objects.count(), 1)

    def test_api_race_fail_closed(self):
        update_handover_content(
            self.handover,
            {
                "title": "Neu",
                "details": "Neu",
                "category": HandoverEntry.Category.MATERIAL,
                "priority": HandoverEntry.Priority.NORMAL,
            },
            self.membership,
        )
        self.handover.refresh_from_db()
        self.assertEqual(self.handover.version, 2)

        response = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data=json.dumps({"version": 1}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], ERROR_CODE_CONFLICT)
        self.assertEqual(HandoverAck.objects.count(), 0)
