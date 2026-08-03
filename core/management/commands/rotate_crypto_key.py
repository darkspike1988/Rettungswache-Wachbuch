"""Re-encrypt at-rest secrets with the currently active master key.

Decouples TOTP-secret encryption from ``SECRET_KEY`` so that a
``SECRET_KEY`` rotation no longer invalidates existing envelopes.

See ``docs/OPERATIONS.md`` (section "Krypto-Schlüsselrotation") for the
end-to-end procedure.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ...crypto_at_rest import (
    MasterKeyError,
    derive_master_key,
    encrypt_secret,
    is_encrypted,
    try_decrypt_with_key,
)
from ...models import TotpDevice


class Command(BaseCommand):
    help = (
        "Re-verschlüsselt alle gespeicherten TOTP-Secrets mit dem aktuell "
        "konfigurierten Master-Key (CRYPTO_MASTER_KEY bzw. HKDF(SECRET_KEY)). "
        "Ermöglicht die Rotation des Krypto-Master-Keys ohne Verlust der "
        "Zweitfaktoren."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur prüfen und Anzahl ausgeben, keine Änderungen speichern.",
        )
        parser.add_argument(
            "--show-current-key",
            action="store_true",
            help=(
                "Gibt den Hex-Wert des aktuell aktiven Master-Keys aus, damit "
                "er während einer Rotation als CRYPTO_PREVIOUS_MASTER_KEY "
                "hinterlegt werden kann. Nimmt keine Änderungen vor."
            ),
        )

    def handle(self, *args, **options):
        if options["show_current_key"]:
            try:
                key_hex = derive_master_key().hex()
            except MasterKeyError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(key_hex)
            return

        try:
            active_key = derive_master_key()
        except MasterKeyError as exc:
            raise CommandError(str(exc)) from exc

        previous_key = None
        try:
            previous_key = derive_master_key(source="previous")
        except MasterKeyError:
            previous_key = None

        devices = TotpDevice.objects.all()
        if not devices.exists():
            self.stdout.write(self.style.SUCCESS(
                "Keine TOTP-Geräte vorhanden – nichts zu rotieren."
            ))
            return

        scanned = pending = stale = broken = 0

        for device in devices.iterator():
            scanned += 1
            current = device.secret or ""

            if is_encrypted(current):
                # Already encrypted: decide whether the active key opens it.
                if try_decrypt_with_key(current, active_key) is not None:
                    # Already on the active key – nothing to do.
                    continue
                if previous_key is not None and try_decrypt_with_key(current, previous_key) is not None:
                    plaintext = try_decrypt_with_key(current, previous_key)
                else:
                    broken += 1
                    continue
            else:
                # Legacy plaintext (pre-0.13) or empty.
                if not current:
                    continue
                stale += 1
                plaintext = current

            if options["dry_run"]:
                pending += 1
                continue

            new_envelope = encrypt_secret(plaintext)
            device.secret = new_envelope
            device.save(update_fields=["secret"])
            pending += 1

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "Dry-Run – es wurden keine Änderungen gespeichert."
            ))
        self.stdout.write(self.style.SUCCESS(
            f"Geprüft: {scanned}  ·  Re-verschlüsselt: {pending}  ·  "
            f"Legacy-Klartext: {stale}  ·  Nicht lesbar: {broken}"
        ))
        if broken:
            self.stderr.write(self.style.ERROR(
                f"{broken} Geheimnis(se) konnten nicht entschlüsselt werden – "
                "CRYPTO_PREVIOUS_MASTER_KEY prüfen oder Datensatz manuell kontrollieren."
            ))
