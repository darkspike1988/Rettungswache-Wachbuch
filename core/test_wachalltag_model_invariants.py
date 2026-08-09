from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Checklist, HandoverEntry, Station
from core.wachalltag_models import (
    AssetEvent,
    ChecklistSchedule,
    Defect,
    DefectAttachment,
    DefectEvent,
    HandoverAck,
    InventoryEvent,
    InventoryItem,
    StationAsset,
)


class WachalltagStationInvariantTests(TestCase):
    def setUp(self):
        self.a = Station.objects.create(name="Wache A", slug="wache-a")
        self.b = Station.objects.create(name="Wache B", slug="wache-b")
        self.user = User.objects.create_user(username="invariant-user", password="test-password")
        self.defect = Defect.objects.create(station=self.a, title="Mangel", created_by=self.user)
        self.asset = StationAsset.objects.create(station=self.a, asset_id="rtw-1", label="RTW 1")
        self.inventory = InventoryItem.objects.create(station=self.a, item_id="key-1", label="Schlüssel")
        self.handover = HandoverEntry.objects.create(
            station=self.a,
            category=HandoverEntry.Category.MATERIAL,
            priority=HandoverEntry.Priority.NORMAL,
            status=HandoverEntry.Status.OPEN,
            title="Übergabe",
            details="Test",
            author=self.user,
        )
        self.checklist = Checklist.objects.create(station=self.a, title="Check")

    def assert_station_mismatch_rejected(self, factory):
        with self.assertRaises(ValidationError):
            factory()

    def test_append_only_children_cannot_claim_another_station(self):
        self.assert_station_mismatch_rejected(
            lambda: DefectEvent.objects.create(
                defect=self.defect,
                station=self.b,
                kind=DefectEvent.Kind.CREATED,
                actor=self.user,
            )
        )
        self.assert_station_mismatch_rejected(
            lambda: AssetEvent.objects.create(
                asset=self.asset,
                station=self.b,
                to_status=StationAsset.Status.READY,
                actor=self.user,
            )
        )
        self.assert_station_mismatch_rejected(
            lambda: InventoryEvent.objects.create(
                item=self.inventory,
                station=self.b,
                action=InventoryEvent.Action.CHECKOUT,
                actor=self.user,
                holder=self.user,
            )
        )
        self.assert_station_mismatch_rejected(
            lambda: HandoverAck.objects.create(
                station=self.b,
                handover=self.handover,
                user=self.user,
            )
        )
        self.assert_station_mismatch_rejected(
            lambda: DefectAttachment.objects.create(
                defect=self.defect,
                station=self.b,
                filename="x.jpg",
                content_type="image/jpeg",
                data=b"x",
                size=1,
                uploaded_by=self.user,
            )
        )

    def test_checklist_schedule_cannot_claim_another_station(self):
        self.assert_station_mismatch_rejected(
            lambda: ChecklistSchedule.objects.create(
                checklist=self.checklist,
                station=self.b,
                interval=ChecklistSchedule.Interval.DAILY,
            )
        )
