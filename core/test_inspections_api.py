import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.api.views import hash_api_token
from core.models import ApiToken, Membership, Station
from core.wachalltag_models import AssetInspection, Defect, StationAsset


class InspectionApiTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Wache Nord", slug="wache-nord")
        self.other = Station.objects.create(name="Sued", slug="sued")
        self.lead = self._user("lead", self.station, Membership.Role.SHIFT_LEAD)
        self.member = self._user("mara", self.station, Membership.Role.MEMBER)
        self.asset = StationAsset.objects.create(
            station=self.station, asset_id="atem-1", label="Atemschutz 1", kind="device"
        )

    def _user(self, name, station, role):
        user = User.objects.create_user(username=name, password="secret-test-password")
        Membership.objects.create(user=user, station=station, role=role)
        raw = f"wb_test_{name}_token_1234567890"
        ApiToken.objects.create(
            user=user,
            label="Tests",
            token_prefix=raw[:11],
            token_hash=hash_api_token(raw),
            scopes=["read:me", "read:handovers", "write:handovers"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        return {"raw": raw, "auth": {"HTTP_AUTHORIZATION": f"Token {raw}"}}

    def _post(self, path, auth, body=None):
        return self.client.post(path, data=json.dumps(body or {}), content_type="application/json", **auth)

    def _put(self, path, auth, body=None):
        return self.client.put(path, data=json.dumps(body or {}), content_type="application/json", **auth)

    # --- schedule -----------------------------------------------------------

    def test_set_schedule_requires_write_role(self):
        response = self._put(
            "/api/v1/assets/atem-1/inspection-schedule/", self.member["auth"], {"interval_days": 365}
        )
        self.assertEqual(response.status_code, 403)

    def test_lead_sets_schedule_then_state_unknown(self):
        response = self._put(
            "/api/v1/assets/atem-1/inspection-schedule/", self.lead["auth"], {"interval_days": 365}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inspection_interval_days"], 365)
        # Interval set but never inspected → state 'unknown'.
        self.assertEqual(response.json()["inspection_state"], "unknown")

    def test_invalid_interval_rejected(self):
        response = self._put(
            "/api/v1/assets/atem-1/inspection-schedule/", self.lead["auth"], {"interval_days": 99999}
        )
        self.assertEqual(response.status_code, 422)

    # --- record inspection --------------------------------------------------

    def test_record_inspection_updates_last_and_state_ok(self):
        self.asset.inspection_interval_days = 30
        self.asset.save(update_fields=["inspection_interval_days"])
        response = self._post(
            "/api/v1/assets/atem-1/inspection/", self.member["auth"], {"result": "ok", "note": "geprüft"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["inspection_state"], "ok")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.last_inspected_at, timezone.localdate())
        self.assertTrue(AssetInspection.objects.filter(asset=self.asset).exists())

    def test_invalid_result_rejected(self):
        response = self._post(
            "/api/v1/assets/atem-1/inspection/", self.member["auth"], {"result": "bogus"}
        )
        self.assertEqual(response.status_code, 422)

    def test_inspection_records_are_append_only(self):
        inspection = AssetInspection.objects.create(
            asset=self.asset, station=self.station, result="ok", performed_by=self.member and User.objects.get(username="mara")
        )
        inspection.note = "geaendert"
        with self.assertRaises(Exception):
            inspection.save()

    # --- due list -----------------------------------------------------------

    def test_due_list_orders_overdue_before_due_soon(self):
        today = timezone.localdate()
        overdue = StationAsset.objects.create(
            station=self.station, asset_id="ov", label="Overdue", kind="device",
            inspection_interval_days=1, last_inspected_at=today - timedelta(days=5),
        )
        due_soon = StationAsset.objects.create(
            station=self.station, asset_id="soon", label="Soon", kind="device",
            inspection_interval_days=30, last_inspected_at=today - timedelta(days=20),
        )
        StationAsset.objects.create(
            station=self.station, asset_id="okk", label="Ok", kind="device",
            inspection_interval_days=30, last_inspected_at=today,
        )
        response = self.client.get("/api/v1/inspections/due/", **self.member["auth"])
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        # 'atem-1' has no interval → excluded; 'okk' is ok → excluded.
        self.assertIn("ov", ids)
        self.assertIn("soon", ids)
        self.assertNotIn("okk", ids)
        self.assertLess(ids.index("ov"), ids.index("soon"))
        _ = (overdue, due_soon)

    # --- device card --------------------------------------------------------

    def test_asset_card_includes_history_and_open_defects(self):
        AssetInspection.objects.create(
            asset=self.asset, station=self.station, result="ok",
            performed_by=User.objects.get(username="lead"),
        )
        Defect.objects.create(
            station=self.station, title="Maske undicht", asset_ref="atem-1",
            created_by=User.objects.get(username="mara"),
        )
        response = self.client.get("/api/v1/assets/atem-1/", **self.member["auth"])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["inspections"]), 1)
        self.assertEqual(len(data["open_defects"]), 1)
        self.assertEqual(data["open_defects"][0]["title"], "Maske undicht")

    def test_cross_station_asset_hidden(self):
        StationAsset.objects.create(station=self.other, asset_id="fremd", label="Fremd", kind="device")
        response = self.client.get("/api/v1/assets/fremd/", **self.member["auth"])
        self.assertEqual(response.status_code, 404)
