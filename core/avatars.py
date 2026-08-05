"""Constrained profile-avatar processing (no general file uploads)."""

from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
AVATAR_SIZE = 192
OUTPUT_CONTENT_TYPE = "image/jpeg"


def process_avatar_upload(uploaded_file):
    """Validate and normalize an avatar to a small JPEG byte string."""
    if uploaded_file is None:
        raise ValidationError("Bitte ein Bild wählen.")
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise ValidationError("Das Bild darf höchstens 2 MB groß sein.")
    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Erlaubt sind JPEG, PNG oder WebP.")
    raw = uploaded_file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValidationError("Das Bild darf höchstens 2 MB groß sein.")
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except UnidentifiedImageError as exc:
        raise ValidationError("Die Datei ist kein gültiges Bild.") from exc
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    image.thumbnail((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), (243, 247, 245))
    offset = ((AVATAR_SIZE - image.width) // 2, (AVATAR_SIZE - image.height) // 2)
    canvas.paste(image, offset)
    buffer = BytesIO()
    canvas.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue(), OUTPUT_CONTENT_TYPE


def initials_for(user):
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if first and last:
        return f"{first[0]}{last[0]}".upper()
    if first:
        return first[:2].upper()
    username = (user.username or "?").strip()
    return username[:2].upper()
