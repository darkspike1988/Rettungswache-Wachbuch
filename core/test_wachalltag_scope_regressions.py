from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.api.views import hash_api_token
from core.models import ApiToken, HandoverEntry, Membership, Station
from core.wachalltag_models import HandoverAck


class WachalltagScopeRegressionTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Scope-Wache", slug="scope-wache")
        self.user = User.objects.create_user(username="readonly", password="test-password")
        Membership.objects.create(
            user=self.user,
            station=self.station,
            role=Membership.Role.MEMBER,
        )
        self.handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.MATERIAL,
            priority=HandoverEntry.Priority.NORMAL,
            status=HandoverEntry.Status.OPEN,
            title="Read-only Übergabe",
            details="Scope-Test",
            author=self.user,
        )
        self.raw_token = "wb_readonly_ack_scope_123456789"
        ApiToken.objects.create(
            user=self.user,
            label="Read only",
            token_prefix=self.raw_token[:11],
            token_hash=hash_api_token(self.raw_token),
            scopes=["read:me", "read:handovers"],
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {self.raw_token}"}

    def test_read_only_token_may_list_but_not_create_acknowledgement(self):
        listed = self.client.get(
            f"/api/v1/handovers/{self.handover.pk}/acks/",
            **self.auth,
        )
        self.assertEqual(listed.status_code, 200)

        write = self.client.post(
            f"/api/v1/handovers/{self.handover.pk}/ack/",
            data="{}",
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(write.status_code, 403)
        self.assertEqual(write.json()["error"]["code"], "forbidden")
        self.assertFalse(HandoverAck.objects.filter(handover=self.handover).exists())
