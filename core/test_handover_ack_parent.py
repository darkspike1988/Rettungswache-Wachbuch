"""Parent regression: malformed web revision strings fail closed."""

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import AuditEvent, HandoverEntry, Membership, Station
from core.services import (
    InvalidHandoverRevision,
    acknowledge_handover,
    update_handover_content,
)
from core.wachalltag_models import HandoverAck


class ServiceRevisionStringTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Parser QA", slug="parser-qa")
        self.user = User.objects.create_user(username="parser-qa")
        self.membership = Membership.objects.create(
            station=self.station,
            user=self.user,
            role=Membership.Role.MEMBER,
        )
        self.handover = HandoverEntry.objects.create(
            station=self.station,
            author=self.user,
            category=HandoverEntry.Category.MATERIAL,
            title="Parser QA",
            details="Neutral QA content",
        )

    def test_unicode_nondigit_integer_and_oversized_integer_fail_closed(self):
        for value in ["²", "1²", "9" * 5000]:
            with self.subTest(input_length=len(value)):
                with self.assertRaises(InvalidHandoverRevision):
                    acknowledge_handover(self.handover, self.membership, value)
                self.assertEqual(HandoverAck.objects.count(), 0)
                self.assertFalse(
                    AuditEvent.objects.filter(action="handover.acknowledged").exists()
                )

    def test_content_audit_records_fields_without_copying_free_text(self):
        import json

        update_handover_content(
            self.handover,
            {"title": "Parent changed title", "details": "Parent changed details"},
            self.membership,
        )
        entry = AuditEvent.objects.get(action="handover.content_updated")
        self.assertEqual(entry.metadata["fields"], ["title", "details"])
        self.assertEqual(entry.metadata["changes"], {})
        self.assertNotIn("Parent changed", json.dumps(entry.metadata))

    def test_web_malformed_revision_does_not_create_ack_or_server_error(self):
        self.client.force_login(self.user)
        for value in ("²", "1²", "9" * 5000):
            with self.subTest(input_length=len(value)):
                response = self.client.post(
                    f"/uebergaben/{self.handover.pk}/quittieren/",
                    {"version": value},
                )
                self.assertEqual(response.status_code, 302)
                self.assertFalse(HandoverAck.objects.exists())
                self.assertFalse(
                    AuditEvent.objects.filter(action="handover.acknowledged").exists()
                )
