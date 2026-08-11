from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .api.views import DEFAULT_MOBILE_SCOPES, generate_api_token
from .models import (
    ApiToken,
    Membership,
    PrivateConversation,
    SecureMail,
    Station,
    UserCryptoIdentity,
)


def make_envelope(recipient_ids):
    """Structurally valid ciphertext envelope (no real crypto needed for API tests)."""
    return {
        "ciphertext": "AAAABBBBCCCC",
        "nonce": "AAAAAAAAAAAA",
        "key_wraps": {
            str(rid): {
                "epk": {"kty": "EC", "crv": "P-256", "x": "AAAA", "y": "BBBB"},
                "wrapped_key": "AAAA.BBBBCCCC",
            }
            for rid in recipient_ids
        },
    }


class ChatApiBase(TestCase):
    def setUp(self):
        self.station = Station.objects.create(name="Testwache", slug="testwache")
        self.other_station = Station.objects.create(name="Andere", slug="andere")
        self.alex = self._member("alex@example.org", "Alex", self.station, Membership.Role.ADMIN)
        self.mara = self._member("mara@example.org", "Mara", self.station, Membership.Role.MEMBER)
        self.foreign = self._member("ext@example.org", "Ext", self.other_station, Membership.Role.MEMBER)

    def _member(self, username, first, station, role):
        user = User.objects.create_user(username, first_name=first)
        Membership.objects.create(user=user, station=station, role=role)
        return user

    def _identity(self, user):
        return UserCryptoIdentity.objects.create(
            user=user,
            public_jwk={"kty": "EC", "crv": "P-256", "x": "AAAA", "y": "BBBB"},
            wrapped_private_jwk="AAAA.BBBB",
            kdf_salt="c2FsdHNhbHRzYWx0",
            kdf_iterations=600000,
        )

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

    def _auth(self, raw):
        return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}

    def _post_json(self, url, raw, payload):
        import json

        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(raw),
        )


class ChatIdentityTests(ChatApiBase):
    def test_default_scopes_include_chat(self):
        self.assertIn("read:chat", DEFAULT_MOBILE_SCOPES)
        self.assertIn("write:chat", DEFAULT_MOBILE_SCOPES)

    def test_identity_get_unconfigured_then_register_then_get(self):
        raw = self._token(self.alex)
        unconfigured = self.client.get(reverse("api_v1_chat_identity"), **self._auth(raw))
        self.assertEqual(unconfigured.status_code, 200)
        self.assertFalse(unconfigured.json()["configured"])

        created = self._post_json(reverse("api_v1_chat_identity"), raw, {
            "public_jwk": {"kty": "EC", "crv": "P-256", "x": "AAAA", "y": "BBBB"},
            "wrapped_private_jwk": "AAAABBBBCCCCDDDD.EEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLL",
            "kdf_salt": "c2FsdHNhbHRzYWx0",
            "kdf_iterations": 600000,
        })
        self.assertEqual(created.status_code, 200)
        self.assertTrue(UserCryptoIdentity.objects.filter(user=self.alex).exists())

        bundle = self.client.get(reverse("api_v1_chat_identity"), **self._auth(raw)).json()
        self.assertTrue(bundle["configured"])
        self.assertEqual(bundle["kdf_iterations"], 600000)

    def test_identity_replace_requires_flag(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        conflict = self._post_json(reverse("api_v1_chat_identity"), raw, {
            "public_jwk": {"kty": "EC", "crv": "P-256", "x": "AAAA", "y": "BBBB"},
            "wrapped_private_jwk": "AAAABBBBCCCCDDDD.EEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLL",
            "kdf_salt": "c2FsdHNhbHRzYWx0",
            "kdf_iterations": 600000,
        })
        self.assertEqual(conflict.status_code, 409)

    def test_member_keys_lists_station_members(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        response = self.client.get(reverse("api_v1_chat_keys"), **self._auth(raw))
        self.assertEqual(response.status_code, 200)
        ids = {m["user_id"] for m in response.json()["members"]}
        self.assertEqual(ids, {self.alex.id, self.mara.id})


class StationChatTests(ChatApiBase):
    def test_send_requires_own_keys(self):
        raw = self._token(self.alex)
        response = self._post_json(reverse("api_v1_chat"), raw, make_envelope([self.alex.id]))
        self.assertEqual(response.status_code, 409)

    def test_send_and_list(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        sent = self._post_json(reverse("api_v1_chat"), raw, make_envelope([self.alex.id]))
        self.assertEqual(sent.status_code, 201)
        listed = self.client.get(reverse("api_v1_chat"), **self._auth(raw))
        self.assertEqual(listed.status_code, 200)
        results = listed.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_encrypted"])
        self.assertTrue(results[0]["is_own"])
        self.assertEqual(results[0]["author_name"], "Alex")
        self.assertIsNotNone(results[0]["wrap"])  # viewer's own wrap included

    def test_send_requires_wraps_for_all_keyed_members(self):
        self._identity(self.alex)
        self._identity(self.mara)
        raw = self._token(self.alex)
        # Missing Mara's wrap → validation error.
        bad = self._post_json(reverse("api_v1_chat"), raw, make_envelope([self.alex.id]))
        self.assertEqual(bad.status_code, 422)
        good = self._post_json(
            reverse("api_v1_chat"), raw, make_envelope([self.alex.id, self.mara.id])
        )
        self.assertEqual(good.status_code, 201)

    def test_read_scope_required(self):
        raw = self._token(self.alex, scopes=["read:me"])
        self.assertEqual(self.client.get(reverse("api_v1_chat"), **self._auth(raw)).status_code, 403)

    def test_module_gate(self):
        self.station.chat_enabled = False
        self.station.save(update_fields=["chat_enabled"])
        raw = self._token(self.alex)
        self.assertEqual(self.client.get(reverse("api_v1_chat"), **self._auth(raw)).status_code, 404)

    def test_auditor_forbidden(self):
        auditor = self._member("aud@example.org", "Aud", self.station, Membership.Role.AUDITOR)
        raw = self._token(auditor)
        self.assertEqual(self.client.get(reverse("api_v1_chat"), **self._auth(raw)).status_code, 403)


class PrivateChatTests(ChatApiBase):
    def test_create_conversation_and_send(self):
        self._identity(self.alex)
        self._identity(self.mara)
        raw = self._token(self.alex)
        created = self._post_json(reverse("api_v1_chat_private"), raw, {"peer_id": self.mara.id})
        self.assertEqual(created.status_code, 201)
        conv_id = created.json()["id"]
        peer_ids = {row["user_id"] for row in created.json()["peer_keys"]}
        self.assertEqual(peer_ids, {self.alex.id, self.mara.id})

        sent = self._post_json(
            reverse("api_v1_chat_private_thread", args=[conv_id]),
            raw,
            make_envelope([self.alex.id, self.mara.id]),
        )
        self.assertEqual(sent.status_code, 201)
        thread = self.client.get(
            reverse("api_v1_chat_private_thread", args=[conv_id]), **self._auth(raw)
        ).json()
        self.assertEqual(len(thread["results"]), 1)
        self.assertEqual(thread["other"]["id"], self.mara.id)

    def test_non_participant_cannot_access_thread(self):
        self._identity(self.alex)
        self._identity(self.mara)
        conversation = PrivateConversation.objects.create(
            station=self.station,
            user_low_id=min(self.alex.id, self.mara.id),
            user_high_id=max(self.alex.id, self.mara.id),
        )
        third = self._member("t@example.org", "Third", self.station, Membership.Role.MEMBER)
        raw = self._token(third)
        response = self.client.get(
            reverse("api_v1_chat_private_thread", args=[conversation.pk]), **self._auth(raw)
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_station_conversation_hidden(self):
        conv = PrivateConversation.objects.create(
            station=self.other_station,
            user_low_id=min(self.foreign.id, self.mara.id),
            user_high_id=max(self.foreign.id, self.mara.id),
        )
        raw = self._token(self.mara)
        response = self.client.get(
            reverse("api_v1_chat_private_thread", args=[conv.pk]), **self._auth(raw)
        )
        self.assertEqual(response.status_code, 404)


class SecureMailTests(ChatApiBase):
    def test_send_and_detail_marks_read(self):
        self._identity(self.alex)
        self._identity(self.mara)
        raw_alex = self._token(self.alex)
        payload = make_envelope([self.alex.id, self.mara.id])
        payload["recipient_ids"] = [self.mara.id]
        sent = self._post_json(reverse("api_v1_post"), raw_alex, payload)
        self.assertEqual(sent.status_code, 201)
        mail_id = sent.json()["id"]

        raw_mara = self._token(self.mara)
        inbox = self.client.get(reverse("api_v1_post"), **self._auth(raw_mara)).json()
        self.assertEqual(len(inbox["received"]), 1)

        detail = self.client.get(
            reverse("api_v1_post_detail", args=[mail_id]), **self._auth(raw_mara)
        ).json()
        self.assertTrue(detail["envelope"]["is_encrypted"])
        self.assertIsNotNone(detail["envelope"]["wrap"])
        recipient = SecureMail.objects.get(pk=mail_id).recipients.get(user=self.mara)
        self.assertIsNotNone(recipient.read_at)

    def test_self_send_rejected(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        payload = make_envelope([self.alex.id])
        payload["recipient_ids"] = [self.alex.id]
        self.assertEqual(self._post_json(reverse("api_v1_post"), raw, payload).status_code, 422)

    def test_outsider_cannot_read_mail(self):
        self._identity(self.alex)
        self._identity(self.mara)
        raw_alex = self._token(self.alex)
        payload = make_envelope([self.alex.id, self.mara.id])
        payload["recipient_ids"] = [self.mara.id]
        mail_id = self._post_json(reverse("api_v1_post"), raw_alex, payload).json()["id"]

        third = self._member("t@example.org", "Third", self.station, Membership.Role.MEMBER)
        raw_third = self._token(third)
        response = self.client.get(
            reverse("api_v1_post_detail", args=[mail_id]), **self._auth(raw_third)
        )
        self.assertEqual(response.status_code, 404)
