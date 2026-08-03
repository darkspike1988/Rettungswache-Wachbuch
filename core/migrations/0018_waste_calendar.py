import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_push_outbox"),
        ("core", "0017_ratelimit"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="waste_calendar_enabled",
            field=models.BooleanField(default=False, verbose_name="Müllkalender aktiv"),
        ),
        migrations.AddField(
            model_name="station",
            name="waste_calendar_label",
            field=models.CharField(
                blank=True, default="Müll", max_length=80,
                verbose_name="Anzeigename der Quelle",
            ),
        ),
        migrations.AddField(
            model_name="station",
            name="waste_calendar_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="HTTPS-ICS-Feed des örtlichen Entsorgers (z. B. AbfallNavi/RegioIT).",
                max_length=600,
                verbose_name="Müllkalender ICS-URL",
            ),
        ),
        migrations.CreateModel(
            name="WasteCollection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("source_url", models.URLField(blank=True, default="", max_length=600)),
                ("source_label", models.CharField(blank=True, default="", max_length=80)),
                ("external_uid", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="waste_collections",
                        to="core.station",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
                "indexes": [
                    models.Index(
                        fields=["station", "starts_at"],
                        name="core_wastec_station_dcf03d_idx",
                    ),
                ],
            },
        ),
    ]
