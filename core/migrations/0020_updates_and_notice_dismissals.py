import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0019_waste_calendar"),
    ]

    operations = [
        migrations.CreateModel(
            name="DismissedNotice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("notice_key", models.CharField(max_length=120)),
                ("dismissed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dismissed_notices",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-dismissed_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "notice_key"),
                        name="unique_user_notice_dismissal",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="UpdateRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("current_version", models.CharField(max_length=40)),
                ("target_version", models.CharField(max_length=40)),
                ("release_url", models.URLField(max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Wartet"),
                            ("running", "Wird installiert"),
                            ("succeeded", "Erfolgreich"),
                            ("failed", "Fehlgeschlagen"),
                            ("cancelled", "Abgebrochen"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("result_message", models.CharField(blank=True, max_length=500)),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="update_requests",
                        to="core.station",
                    ),
                ),
            ],
            options={
                "ordering": ["-requested_at"],
                "indexes": [
                    models.Index(
                        fields=["status", "requested_at"],
                        name="core_update_status_2f8a99_idx",
                    )
                ],
            },
        ),
    ]
