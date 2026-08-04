from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_merge_0017_branches"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="waste_calendar_enabled",
            field=models.BooleanField(default=False, verbose_name="Muellkalender aktiviert"),
        ),
        migrations.AddField(
            model_name="station",
            name="waste_calendar_url",
            field=models.URLField(
                blank=True,
                default="",
                max_length=600,
                verbose_name="Muellkalender-ICS-URL",
            ),
        ),
        migrations.CreateModel(
            name="WasteCollection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="waste_collections",
                        to="core.station",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
                "indexes": [models.Index(fields=["station", "starts_at"], name="waste_coll_station_idx")],
            },
        ),
    ]
