import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.api.views import hash_api_token
from core.models import ApiToken, MemberQualification, Membership, Station


class QualificationApiTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(
            name="Wache Nord", slug="wache-nord", qualifications_enabled=True
        )
        self.other = Station.objects.create(name="Sued", slug="sued", qualifications_enabled=True)
        self.admin = self._user("alex", self.station, Membership.Role.ADMIN)
        self.member = self._user("mara", self.station, Membership.Role.MEMBER)
        self.foreign = self._user("ext", self.other, Membership.Role.MEMBER)

    def _user(self, name, station, role):
        user = User.objects.create_user(username=name, password="secret-test-password")
        Membership.objects.create(user=user, station=station, role=role)
        raw = f"wb_test_{name}_token_1234567890"
        ApiToken.objects.create(
            user=user,
            label="Tests",
            token_prefix=raw[:11],
            token_hash=hash_api_token(raw),
            scopes=["read:me", "read:qualifications", "write:qualifications"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        return {"user": user, "auth": {"HTTP_AUTHORIZATION": f"Token {raw}"}}

    def _post(self, path, auth, body):
        return self.client.post(path, data=json.dumps(body), content_type="application/json", **auth)

    def _patch(self, path, auth, body):
        return self.client.patch(path, data=json.dumps(body), content_type="application/json", **auth)

    # --- module gate --------------------------------------------------------

    def test_module_gate(self):
        self.station.qualifications_enabled = False
        self.station.save(update_fields=["qualifications_enabled"])
        response = self.client.get("/api/v1/qualifikationen/", **self.member["auth"])
        self.assertEqual(response.status_code, 404)

    # --- create + visibility ------------------------------------------------

    def test_manager_creates_and_member_sees_own(self):
        created = self._post("/api/v1/qualifikationen/", self.admin["auth"], {
            "user_id": self.member["user"].id,
            "title": "Atemschutz G26",
            "expires_at": (timezone.localdate() + timedelta(days=200)).isoformat(),
        })
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["state"], "valid")
        self.assertEqual(created.json()["member"]["id"], self.member["user"].id)

        mine = self.client.get("/api/v1/qualifikationen/", **self.member["auth"]).json()
        self.assertFalse(mine["is_manager"])
        self.assertEqual(len(mine["results"]), 1)
        self.assertEqual(mine["results"][0]["title"], "Atemschutz G26")

    def test_member_cannot_create(self):
        response = self._post("/api/v1/qualifikationen/", self.member["auth"], {
            "user_id": self.member["user"].id, "title": "X",
        })
        self.assertEqual(response.status_code, 403)

    def test_create_rejects_foreign_member(self):
        response = self._post("/api/v1/qualifikationen/", self.admin["auth"], {
            "user_id": self.foreign["user"].id, "title": "X",
        })
        self.assertEqual(response.status_code, 422)

    def test_manager_sees_all_with_member_info(self):
        MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Führerschein C",
            created_by=self.admin["user"],
        )
        listed = self.client.get("/api/v1/qualifikationen/", **self.admin["auth"]).json()
        self.assertTrue(listed["is_manager"])
        self.assertEqual(listed["results"][0]["member"]["id"], self.member["user"].id)
        member_ids = {m["id"] for m in listed["members"]}
        self.assertEqual(member_ids, {self.admin["user"].id, self.member["user"].id})

    # --- state --------------------------------------------------------------

    def test_state_expired_and_expiring(self):
        today = timezone.localdate()
        MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Abgelaufen",
            expires_at=today - timedelta(days=1), created_by=self.admin["user"],
        )
        MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Bald",
            expires_at=today + timedelta(days=10), created_by=self.admin["user"],
        )
        MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Ohne Frist",
            created_by=self.admin["user"],
        )
        due = self.client.get("/api/v1/qualifikationen/faellig/", **self.admin["auth"]).json()
        titles = [row["title"] for row in due["results"]]
        self.assertEqual(titles, ["Abgelaufen", "Bald"])  # sorted expired first

    def test_due_list_manager_only(self):
        response = self.client.get("/api/v1/qualifikationen/faellig/", **self.member["auth"])
        self.assertEqual(response.status_code, 403)

    # --- update / delete ----------------------------------------------------

    def test_update_and_delete(self):
        item = MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Alt", created_by=self.admin["user"],
        )
        updated = self._patch(f"/api/v1/qualifikationen/{item.pk}/", self.admin["auth"], {"title": "Neu"})
        self.assertEqual(updated.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.title, "Neu")
        deleted = self.client.delete(f"/api/v1/qualifikationen/{item.pk}/", **self.admin["auth"])
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(MemberQualification.objects.filter(pk=item.pk).exists())

    def test_member_cannot_update(self):
        item = MemberQualification.objects.create(
            station=self.station, user=self.member["user"], title="Alt", created_by=self.admin["user"],
        )
        response = self._patch(f"/api/v1/qualifikationen/{item.pk}/", self.member["auth"], {"title": "Neu"})
        self.assertEqual(response.status_code, 403)

    def test_cross_station_detail_hidden(self):
        item = MemberQualification.objects.create(
            station=self.other, user=self.foreign["user"], title="Fremd", created_by=self.foreign["user"],
        )
        response = self._patch(f"/api/v1/qualifikationen/{item.pk}/", self.admin["auth"], {"title": "X"})
        self.assertEqual(response.status_code, 404)

    def test_auditor_has_no_access(self):
        auditor = self._user("aud", self.station, Membership.Role.AUDITOR)
        response = self.client.get("/api/v1/qualifikationen/", **auditor["auth"])
        self.assertEqual(response.status_code, 403)

    def test_scope_required(self):
        raw = "wb_noscope_token_123456"
        ApiToken.objects.create(
            user=self.member["user"], label="x", token_prefix=raw[:11],
            token_hash=hash_api_token(raw), scopes=["read:me"],
            expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(
            "/api/v1/qualifikationen/", HTTP_AUTHORIZATION=f"Token {raw}"
        )
        self.assertEqual(response.status_code, 403)
