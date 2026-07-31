from django.db import migrations


def encrypt_existing_totp_secrets(apps, schema_editor):
    from core.crypto_at_rest import encrypt_secret, is_encrypted

    TotpDevice = apps.get_model("core", "TotpDevice")
    for device in TotpDevice.objects.all().iterator():
        if not device.secret or is_encrypted(device.secret):
            continue
        device.secret = encrypt_secret(device.secret)
        device.save(update_fields=["secret"])


def noop_reverse(apps, schema_editor):
    # Decryption would leave secrets recoverable; leave encrypted on reverse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_totp_secret_aes_gcm"),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_totp_secrets, noop_reverse),
    ]
