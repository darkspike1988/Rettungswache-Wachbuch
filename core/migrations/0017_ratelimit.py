from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_station_payment_hints"),
    ]

    operations = [
        migrations.CreateModel(
            name="RateLimit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bucket", models.CharField(max_length=64)),
                ("key_hash", models.CharField(max_length=64)),
                ("window_start", models.DateTimeField()),
                ("count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["bucket", "window_start"]),
                ],
                "unique_together": {("bucket", "key_hash", "window_start")},
            },
        ),
    ]
