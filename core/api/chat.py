"""Versioned JSON API for E2EE messaging (Wachenchat, private 1:1, Secure Mail).

The server stores and forwards ciphertext envelopes only and never decrypts.
The wire format matches the web client exactly (``A256GCM+ECDH-ES``):
CEK/AES-256-GCM message body plus per-recipient ECDH-P256 + HKDF-SHA256 key
wraps. See ``core/messaging.py`` and ``docs/CRYPTO-BSI.md``.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from ..access import CONTENT_ROLES
from ..messaging import (
    ordered_pair,
    public_keys_for_users,
    serialize_message_for_client,
    station_content_users,
    user_can_access_conversation,
    validate_encrypted_payload,
)
from ..models import (
    ChatMessage,
    PrivateConversation,
    PrivateMessage,
    SecureMail,
    SecureMailRecipient,
    UserCryptoIdentity,
)
from ..services import audit
from .views import (
    API_VERSION,
    _json_error,
    _parse_json,
    _scope_allowed,
    api_token_required,
)


def _person_name(user):
    if user is None:
        return ""
    return user.first_name or user.username


def _feed_item(message, viewer):
    data = serialize_message_for_client(message, viewer.id)
    author = getattr(message, "author", None) or getattr(message, "sender", None)
    data["author_name"] = _person_name(author)
    data["is_own"] = data.get("author_id") == viewer.id
    return data


def _require_chat_module(request):
    if not request.membership.station.chat_enabled:
        return _json_error(request, "Modul ist nicht aktiviert.", status=404)
    return None


def _require_content_role(request):
    if request.membership.role not in CONTENT_ROLES:
        return _json_error(request, "Rolle hat keinen Zugriff auf Nachrichten.", status=403)
    return None


# --- Crypto identity --------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def identity(request):
    """GET own key bundle (for unlock) / POST register or replace identity."""
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:chat"):
            return _json_error(request, "Scope write:chat fehlt.", status=403)
        body = _parse_json(request)
        if not body:
            return _json_error(request, "JSON-Körper erwartet.")
        public_jwk = body.get("public_jwk")
        wrapped = body.get("wrapped_private_jwk")
        salt = body.get("kdf_salt")
        try:
            iterations = int(body.get("kdf_iterations") or 600_000)
        except (TypeError, ValueError):
            return _json_error(request, "KDF-Iterationen ungültig.", status=422)
        if (
            not isinstance(public_jwk, dict)
            or public_jwk.get("kty") != "EC"
            or public_jwk.get("crv") != "P-256"
        ):
            return _json_error(request, "Öffentlicher Schlüssel ungültig.", status=422)
        if not isinstance(wrapped, str) or not (32 <= len(wrapped) <= 8000):
            return _json_error(request, "Privater Schlüsselumschlag ungültig.", status=422)
        if not isinstance(salt, str) or not (16 <= len(salt) <= 128):
            return _json_error(request, "Salt ungültig.", status=422)
        if not (100_000 <= iterations <= 1_000_000):
            return _json_error(request, "KDF-Iterationen ungültig.", status=422)
        existing = UserCryptoIdentity.objects.filter(user=request.user).first()
        if existing and not body.get("replace"):
            return _json_error(request, "Schlüssel existieren bereits.", status=409)
        with transaction.atomic():
            obj, _ = UserCryptoIdentity.objects.update_or_create(
                user=request.user,
                defaults={
                    "public_jwk": {
                        "kty": "EC",
                        "crv": "P-256",
                        "x": public_jwk.get("x"),
                        "y": public_jwk.get("y"),
                    },
                    "wrapped_private_jwk": wrapped,
                    "kdf_salt": salt,
                    "kdf_iterations": iterations,
                },
            )
            audit(request.user, request.membership.station, "crypto.keys_upserted", obj, {
                "fields": ["public_jwk"],
            })
        return JsonResponse({"ok": True})

    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    obj = UserCryptoIdentity.objects.filter(user=request.user).first()
    if not obj:
        return JsonResponse({"ok": True, "configured": False})
    return JsonResponse({
        "ok": True,
        "configured": True,
        "user_id": request.user.id,
        "public_jwk": obj.public_jwk,
        "wrapped_private_jwk": obj.wrapped_private_jwk,
        "kdf_salt": obj.kdf_salt,
        "kdf_iterations": obj.kdf_iterations,
    })


@csrf_exempt
@require_GET
@api_token_required
def member_keys(request):
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    role_error = _require_content_role(request)
    if role_error:
        return role_error
    users = station_content_users(request.membership.station)
    return JsonResponse({"ok": True, "members": public_keys_for_users(users)})


# --- Station chat (Wachenchat) ---------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def station_chat(request):
    station = request.membership.station
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:chat"):
            return _json_error(request, "Scope write:chat fehlt.", status=403)
        role_error = _require_content_role(request)
        if role_error:
            return role_error
        body = _parse_json(request)
        if body is None:
            return _json_error(request, "JSON-Körper erwartet.")
        members = list(station_content_users(station))
        keyed_ids = set(
            UserCryptoIdentity.objects.filter(user__in=members).values_list("user_id", flat=True)
        )
        if request.user.id not in keyed_ids:
            return _json_error(request, "Eigene Schlüssel fehlen. Bitte zuerst Schlüssel einrichten.", status=409)
        required = set(keyed_ids) | {request.user.id}
        try:
            payload = validate_encrypted_payload(body, required_recipient_ids=required)
        except DjangoValidationError as exc:
            return _json_error(request, " ".join(exc.messages), status=422)
        message = ChatMessage.objects.create(
            station=station,
            author=request.user,
            body="",
            ciphertext=payload["ciphertext"],
            nonce=payload["nonce"],
            key_wraps=payload["key_wraps"],
            algo=payload["algo"],
            is_encrypted=True,
        )
        audit(request.user, station, "chat.message_created", message, {
            "fields": ["ciphertext"],
            "encrypted": True,
        })
        return JsonResponse({"ok": True, "id": message.pk}, status=201)

    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    role_error = _require_content_role(request)
    if role_error:
        return role_error
    rows = list(
        ChatMessage.objects.filter(station=station, is_hidden=False)
        .select_related("author")
        .order_by("-created_at")[:80]
    )
    rows.reverse()
    return JsonResponse({
        "ok": True,
        "api_version": API_VERSION,
        "results": [_feed_item(item, request.user) for item in rows],
    })


# --- Private 1:1 chat -------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def private_home(request):
    station = request.membership.station
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:chat"):
            return _json_error(request, "Scope write:chat fehlt.", status=403)
        role_error = _require_content_role(request)
        if role_error:
            return role_error
        body = _parse_json(request) or {}
        try:
            peer_id = int(body.get("peer_id"))
        except (TypeError, ValueError):
            return _json_error(request, "Bitte einen Kollegen wählen.", status=422)
        peer = station_content_users(station).filter(pk=peer_id).first()
        if peer is None:
            return _json_error(request, "Nicht gefunden.", status=404)
        try:
            low, high = ordered_pair(request.user.id, peer.id)
        except DjangoValidationError as exc:
            return _json_error(request, " ".join(exc.messages), status=422)
        conversation, _ = PrivateConversation.objects.get_or_create(
            station=station, user_low_id=low, user_high_id=high
        )
        return JsonResponse({
            "ok": True,
            "id": conversation.pk,
            "peer_keys": public_keys_for_users([request.user, peer]),
        }, status=201)

    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    role_error = _require_content_role(request)
    if role_error:
        return role_error
    conversations = (
        PrivateConversation.objects.filter(station=station)
        .filter(Q(user_low=request.user) | Q(user_high=request.user))
        .select_related("user_low", "user_high")
        .order_by("-updated_at")[:50]
    )
    results = []
    for item in conversations:
        other = item.other_user(request.user)
        results.append({
            "id": item.pk,
            "other_id": other.id,
            "other_name": _person_name(other),
            "updated_at": item.updated_at.isoformat(),
        })
    colleagues = public_keys_for_users(
        station_content_users(station).exclude(pk=request.user.pk)
    )
    return JsonResponse({"ok": True, "results": results, "colleagues": colleagues})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def private_thread(request, pk):
    station = request.membership.station
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    conversation = PrivateConversation.objects.filter(pk=pk, station=station).first()
    if conversation is None or not user_can_access_conversation(request.user, conversation):
        return _json_error(request, "Nicht gefunden.", status=404)
    other = conversation.other_user(request.user)
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:chat"):
            return _json_error(request, "Scope write:chat fehlt.", status=403)
        role_error = _require_content_role(request)
        if role_error:
            return role_error
        body = _parse_json(request)
        if body is None:
            return _json_error(request, "JSON-Körper erwartet.")
        try:
            payload = validate_encrypted_payload(
                body, required_recipient_ids={request.user.id, other.id}
            )
        except DjangoValidationError as exc:
            return _json_error(request, " ".join(exc.messages), status=422)
        message = PrivateMessage.objects.create(
            conversation=conversation,
            author=request.user,
            ciphertext=payload["ciphertext"],
            nonce=payload["nonce"],
            key_wraps=payload["key_wraps"],
            algo=payload["algo"],
        )
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        audit(request.user, station, "private_chat.message_created", message, {
            "fields": ["ciphertext"],
        })
        return JsonResponse({"ok": True, "id": message.pk}, status=201)

    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    role_error = _require_content_role(request)
    if role_error:
        return role_error
    rows = list(
        PrivateMessage.objects.filter(conversation=conversation, is_hidden=False)
        .select_related("author")
        .order_by("-created_at")[:80]
    )
    rows.reverse()
    return JsonResponse({
        "ok": True,
        "other": {"id": other.id, "name": _person_name(other)},
        "peer_keys": public_keys_for_users([request.user, other]),
        "results": [_feed_item(item, request.user) for item in rows],
    })


# --- Secure Mail ------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def mail_inbox(request):
    station = request.membership.station
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:chat"):
            return _json_error(request, "Scope write:chat fehlt.", status=403)
        role_error = _require_content_role(request)
        if role_error:
            return role_error
        body = _parse_json(request)
        if body is None:
            return _json_error(request, "JSON-Körper erwartet.")
        recipient_ids = body.get("recipient_ids") or []
        if not isinstance(recipient_ids, list) or not recipient_ids:
            return _json_error(request, "Bitte Empfänger wählen.", status=422)
        try:
            recipient_ids = sorted({int(item) for item in recipient_ids})
        except (TypeError, ValueError):
            return _json_error(request, "Empfänger ungültig.", status=422)
        if request.user.id in recipient_ids:
            return _json_error(request, "Eigenversand ist nicht vorgesehen.", status=422)
        allowed = set(
            station_content_users(station)
            .filter(pk__in=recipient_ids)
            .values_list("id", flat=True)
        )
        if set(recipient_ids) != allowed:
            return _json_error(request, "Empfänger gehören nicht zur Wache.", status=422)
        required = set(recipient_ids) | {request.user.id}
        try:
            payload = validate_encrypted_payload(body, required_recipient_ids=required)
        except DjangoValidationError as exc:
            return _json_error(request, " ".join(exc.messages), status=422)
        with transaction.atomic():
            mail = SecureMail.objects.create(
                station=station,
                sender=request.user,
                ciphertext=payload["ciphertext"],
                nonce=payload["nonce"],
                key_wraps=payload["key_wraps"],
                algo=payload["algo"],
            )
            SecureMailRecipient.objects.bulk_create([
                SecureMailRecipient(mail=mail, user_id=user_id) for user_id in recipient_ids
            ])
            audit(request.user, station, "secure_mail.created", mail, {
                "fields": ["ciphertext", "recipients"],
                "recipient_count": len(recipient_ids),
            })
        return JsonResponse({"ok": True, "id": mail.pk}, status=201)

    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    role_error = _require_content_role(request)
    if role_error:
        return role_error
    received = (
        SecureMail.objects.filter(station=station, recipients__user=request.user)
        .select_related("sender")
        .distinct()
        .order_by("-created_at")[:40]
    )
    sent = (
        SecureMail.objects.filter(station=station, sender=request.user)
        .select_related("sender")
        .order_by("-created_at")[:40]
    )

    def _meta(mail):
        return {
            "id": mail.pk,
            "sender": {"id": mail.sender_id, "name": _person_name(mail.sender)},
            "created_at": mail.created_at.isoformat(),
        }

    colleagues = public_keys_for_users(
        station_content_users(station).exclude(pk=request.user.pk)
    )
    return JsonResponse({
        "ok": True,
        "received": [_meta(mail) for mail in received],
        "sent": [_meta(mail) for mail in sent],
        "colleagues": colleagues,
    })


@csrf_exempt
@require_GET
@api_token_required
def mail_detail(request, pk):
    station = request.membership.station
    module_error = _require_chat_module(request)
    if module_error:
        return module_error
    if not _scope_allowed(request.api_token, "read:chat"):
        return _json_error(request, "Scope read:chat fehlt.", status=403)
    mail = SecureMail.objects.filter(pk=pk, station=station).first()
    if mail is None:
        return _json_error(request, "Nicht gefunden.", status=404)
    is_recipient = SecureMailRecipient.objects.filter(mail=mail, user=request.user).exists()
    if mail.sender_id != request.user.id and not is_recipient:
        return _json_error(request, "Nicht gefunden.", status=404)
    if is_recipient:
        SecureMailRecipient.objects.filter(
            mail=mail, user=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
    envelope = serialize_message_for_client(mail, request.user.id)
    envelope["author_name"] = _person_name(mail.sender)
    recipients = [
        {
            "id": recipient.user_id,
            "name": _person_name(recipient.user),
            "read": bool(recipient.read_at),
        }
        for recipient in mail.recipients.select_related("user")
    ]
    return JsonResponse({"ok": True, "envelope": envelope, "recipients": recipients})
