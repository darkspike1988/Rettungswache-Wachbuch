import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def copy_import_timestamps(apps, schema_editor):
    FeedItem = apps.get_model("core", "FeedItem")
    for item in FeedItem.objects.all().iterator():
        stamp = item.imported_at or django.utils.timezone.now()
        item.first_imported_at = stamp
        item.last_seen_at = stamp
        item.save(update_fields=["first_imported_at", "last_seen_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_station_tasks"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="feeditem",
            name="first_imported_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="feeditem",
            name="last_seen_at",
            field=models.DateTimeField(db_index=True, null=True),
        ),
        migrations.RunPython(copy_import_timestamps, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="feeditem",
            name="imported_at",
        ),
        migrations.AlterField(
            model_name="feeditem",
            name="first_imported_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="feeditem",
            name="last_seen_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterModelOptions(
            name="feeditem",
            options={
                "ordering": [
                    models.OrderBy(models.F("published_at"), descending=True, nulls_last=True),
                    "-last_seen_at",
                ],
            },
        ),
        migrations.CreateModel(
            name="TotpDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret", models.CharField(max_length=64)),
                ("is_confirmed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="totp_device",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
