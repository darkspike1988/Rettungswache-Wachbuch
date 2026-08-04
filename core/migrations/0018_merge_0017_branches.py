from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_push_outbox"),
        ("core", "0017_ratelimit"),
    ]

    operations = []
