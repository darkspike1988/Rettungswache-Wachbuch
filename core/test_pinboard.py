from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .api.views import DEFAULT_MOBILE_SCOPES, generate_api_token
from .models import ApiToken, AuditEvent, Membership, PinboardNote, Station


class PinboardBase(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Testwache", slug="testwache")
        self.other = Station.objects.create(name="Andere", slug="andere")
        self.member = User.objects.create_user("member@example.org", first_name="Mara")
        self.membership = Membership.objects.create(
            user=self.member, station=self.station, role=Membership.Role.MEMBER
        )
        self.admin = User.objects.create_user("admin@example.org", first_name="Alex")
        self.admin_membership = Membership.objects.create(
            user=self.admin, station=self.station, role=Membership.Role.ADMIN
        )

    def _note(self, station=None, author=None, **kwargs):
        return PinboardNote.objects.create(
            station=station or self.station,
            author=author or self.member,
            title=kwargs.get("title", "Aushang"),
            body=kwargs.get("body", "Kurzer Hinweis"),
            category=kwargs.get("category", PinboardNote.Category.INFO),
            is_pinned=kwargs.get("is_pinned", False),
        )


class PinboardWebTests(PinboardBase):
    def test_member_can_create_note_and_audit_written(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("pinboard_create"), {
            "title": "Kaffee alle",
            "body": "Bitte nachbestellen",
            "category": PinboardNote.Category.INFO,
        })
        self.assertRedirects(response, reverse("pinboard"))
        note = PinboardNote.objects.get(title="Kaffee alle")
        self.assertEqual(note.station, self.station)
        self.assertEqual(note.author, self.member)
        self.assertTrue(
            AuditEvent.objects.filter(action="pinboard.note_created", object_id=str(note.pk)).exists()
        )

    def test_audit_metadata_has_no_free_text_body(self):
        self.client.force_login(self.member)
        self.client.post(reverse("pinboard_create"), {
            "title": "Geheim-Titel",
            "body": "Sensibler Freitext",
            "category": PinboardNote.Category.INFO,
        })
        event = AuditEvent.objects.get(action="pinboard.note_created")
        self.assertNotIn("Sensibler Freitext", str(event.metadata))
        self.assertEqual(event.metadata.get("fields"), ["title", "category"])

    def test_list_hidden_when_module_disabled(self):
        self.station.pinboard_enabled = False
        self.station.save(update_fields=["pinboard_enabled"])
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("pinboard")).status_code, 404)

    def test_list_only_shows_own_station_and_not_archived(self):
        mine = self._note(title="Meins")
        self._note(station=self.other, author=self.admin, title="Fremd")
        archived = self._note(title="Archiviert")
        archived.is_archived = True
        archived.save(update_fields=["is_archived"])
        self.client.force_login(self.member)
        html = self.client.get(reverse("pinboard")).content.decode()
        self.assertIn("Meins", html)
        self.assertNotIn("Fremd", html)
        self.assertNotIn("Archiviert", html)

    def test_cross_station_edit_returns_404(self):
        foreign = self._note(station=self.other, author=self.admin)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("pinboard_edit", args=[foreign.pk])).status_code, 404
        )

    def test_member_cannot_pin(self):
        note = self._note()
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(reverse("pinboard_pin", args=[note.pk])).status_code, 403
        )
        note.refresh_from_db()
        self.assertFalse(note.is_pinned)

    def test_admin_can_pin_and_toggle(self):
        note = self._note()
        self.client.force_login(self.admin)
        self.client.post(reverse("pinboard_pin", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_pinned)
        self.client.post(reverse("pinboard_pin", args=[note.pk]))
        note.refresh_from_db()
        self.assertFalse(note.is_pinned)

    def test_author_can_archive_own_note(self):
        note = self._note()
        self.client.force_login(self.member)
        self.client.post(reverse("pinboard_archive", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_archived)

    def test_member_cannot_archive_foreign_author_note(self):
        note = self._note(author=self.admin)
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(reverse("pinboard_archive", args=[note.pk])).status_code, 403
        )

    def test_auditor_has_no_access(self):
        auditor_user = User.objects.create_user("auditor@example.org")
        Membership.objects.create(
            user=auditor_user, station=self.station, role=Membership.Role.AUDITOR
        )
        self.client.force_login(auditor_user)
        self.assertEqual(self.client.get(reverse("pinboard")).status_code, 403)


class PinboardApiTests(PinboardBase):
    def _token(self, user, scopes=None):
        raw, token_hash, prefix = generate_api_token()
        ApiToken.objects.create(
            user=user,
            label="Test",
            token_prefix=prefix,
            token_hash=token_hash,
            scopes=list(scopes if scopes is not None else DEFAULT_MOBILE_SCOPES),
        )
        return raw

    def test_default_scopes_include_pinboard(self):
        self.assertIn("read:pinboard", DEFAULT_MOBILE_SCOPES)
        self.assertIn("write:pinboard", DEFAULT_MOBILE_SCOPES)

    def test_api_list_and_create(self):
        raw = self._token(self.member)
        self._note(title="Bestehend")
        listed = self.client.get(reverse("api_v1_pinnwand"), HTTP_AUTHORIZATION=f"Bearer {raw}")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)
        created = self.client.post(
            reverse("api_v1_pinnwand"),
            data='{"title": "Neu per API", "body": "Text", "category": "info"}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw}",
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(PinboardNote.objects.filter(title="Neu per API", station=self.station).exists())

    def test_api_requires_scope(self):
        raw = self._token(self.member, scopes=["read:me"])
        listed = self.client.get(reverse("api_v1_pinnwand"), HTTP_AUTHORIZATION=f"Bearer {raw}")
        self.assertEqual(listed.status_code, 403)

    def test_api_module_disabled_returns_404(self):
        self.station.pinboard_enabled = False
        self.station.save(update_fields=["pinboard_enabled"])
        raw = self._token(self.member)
        listed = self.client.get(reverse("api_v1_pinnwand"), HTTP_AUTHORIZATION=f"Bearer {raw}")
        self.assertEqual(listed.status_code, 404)

    def test_me_advertises_pinboard_module(self):
        raw = self._token(self.member)
        me = self.client.get(reverse("api_v1_me"), HTTP_AUTHORIZATION=f"Bearer {raw}")
        self.assertIn("pinboard", me.json()["membership"]["station"]["modules"])
