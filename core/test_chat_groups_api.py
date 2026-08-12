from django.urls import reverse

from .models import ChatGroup, ChatGroupMember, GroupMessage, Membership
from .test_chat_api import ChatApiBase, make_envelope


class ChatGroupApiTests(ChatApiBase):
    def _group(self, creator, members):
        group = ChatGroup.objects.create(station=self.station, name="Team A", created_by=creator)
        for user in members:
            ChatGroupMember.objects.create(group=group, user=user)
        return group

    def test_create_group_and_list(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        created = self._post_json(reverse("api_v1_chat_groups"), raw, {
            "name": "Frühschicht",
            "member_ids": [self.mara.id],
        })
        self.assertEqual(created.status_code, 201)
        group_id = created.json()["id"]
        self.assertEqual(
            set(ChatGroupMember.objects.filter(group_id=group_id).values_list("user_id", flat=True)),
            {self.alex.id, self.mara.id},
        )
        listed = self.client.get(reverse("api_v1_chat_groups"), **self._auth(raw)).json()
        self.assertEqual(len(listed["results"]), 1)
        self.assertEqual(listed["results"][0]["member_count"], 2)

    def test_create_group_rejects_foreign_members(self):
        self._identity(self.alex)
        raw = self._token(self.alex)
        response = self._post_json(reverse("api_v1_chat_groups"), raw, {
            "name": "X",
            "member_ids": [self.foreign.id],
        })
        self.assertEqual(response.status_code, 422)

    def test_non_member_cannot_see_or_open_group(self):
        group = self._group(self.alex, [self.alex])
        raw = self._token(self.mara)
        listed = self.client.get(reverse("api_v1_chat_groups"), **self._auth(raw)).json()
        self.assertEqual(listed["results"], [])
        detail = self.client.get(
            reverse("api_v1_chat_group_detail", args=[group.pk]), **self._auth(raw)
        )
        self.assertEqual(detail.status_code, 404)

    def test_send_and_read_group_message(self):
        self._identity(self.alex)
        self._identity(self.mara)
        group = self._group(self.alex, [self.alex, self.mara])
        raw = self._token(self.alex)
        # Missing Mara's wrap → 422.
        bad = self._post_json(
            reverse("api_v1_chat_group_detail", args=[group.pk]),
            raw,
            make_envelope([self.alex.id]),
        )
        self.assertEqual(bad.status_code, 422)
        good = self._post_json(
            reverse("api_v1_chat_group_detail", args=[group.pk]),
            raw,
            make_envelope([self.alex.id, self.mara.id]),
        )
        self.assertEqual(good.status_code, 201)
        detail = self.client.get(
            reverse("api_v1_chat_group_detail", args=[group.pk]), **self._auth(raw)
        ).json()
        self.assertEqual(len(detail["results"]), 1)
        self.assertTrue(detail["results"][0]["is_own"])
        self.assertEqual({m["user_id"] for m in detail["members"]}, {self.alex.id, self.mara.id})

    def test_send_requires_own_keys(self):
        group = self._group(self.alex, [self.alex])
        raw = self._token(self.alex)
        response = self._post_json(
            reverse("api_v1_chat_group_detail", args=[group.pk]),
            raw,
            make_envelope([self.alex.id]),
        )
        self.assertEqual(response.status_code, 409)

    def test_manager_can_add_and_remove_members(self):
        group = self._group(self.alex, [self.alex])
        raw = self._token(self.alex)
        added = self._post_json(
            reverse("api_v1_chat_group_members", args=[group.pk]),
            raw,
            {"add": [self.mara.id]},
        )
        self.assertEqual(added.status_code, 200)
        self.assertTrue(ChatGroupMember.objects.filter(group=group, user=self.mara).exists())
        removed = self._post_json(
            reverse("api_v1_chat_group_members", args=[group.pk]),
            raw,
            {"remove": [self.mara.id]},
        )
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(ChatGroupMember.objects.filter(group=group, user=self.mara).exists())

    def test_creator_cannot_be_removed(self):
        group = self._group(self.alex, [self.alex, self.mara])
        raw = self._token(self.alex)
        self._post_json(
            reverse("api_v1_chat_group_members", args=[group.pk]),
            raw,
            {"remove": [self.alex.id]},
        )
        self.assertTrue(ChatGroupMember.objects.filter(group=group, user=self.alex).exists())

    def test_non_manager_cannot_manage_members(self):
        group = self._group(self.alex, [self.alex, self.mara])
        raw = self._token(self.mara)
        response = self._post_json(
            reverse("api_v1_chat_group_members", args=[group.pk]),
            raw,
            {"add": []},
        )
        self.assertEqual(response.status_code, 403)

    def test_cross_station_group_hidden(self):
        foreign_group = ChatGroup.objects.create(
            station=self.other_station, name="Fremd", created_by=self.foreign
        )
        ChatGroupMember.objects.create(group=foreign_group, user=self.foreign)
        raw = self._token(self.alex)
        response = self.client.get(
            reverse("api_v1_chat_group_detail", args=[foreign_group.pk]), **self._auth(raw)
        )
        self.assertEqual(response.status_code, 404)
