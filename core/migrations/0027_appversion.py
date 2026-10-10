import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_station_organization_profile"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "platform",
                    models.CharField(
                        choices=[("web", "Web"), ("android", "Android"), ("ios", "iOS")],
                        max_length=20,
                        verbose_name="Plattform",
                    ),
                ),
                ("version", models.CharField(max_length=20, verbose_name="Version")),
                (
                    "version_code",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="Versionscode"),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Nur aktive Versionen werden für Updates angezeigt",
                        verbose_name="Aktiv",
                    ),
                ),
                ("release_date", models.DateField(verbose_name="Veröffentlichungsdatum")),
                (
                    "download_url",
                    models.URLField(
                        blank=True,
                        help_text="URL zum Herunterladen dieser Version",
                        max_length=500,
                        verbose_name="Download-URL",
                    ),
                ),
                (
                    "changelog",
                    models.TextField(
                        blank=True,
                        help_text="Markdown-Format: ## Version (Datum)\n- Änderung 1\n- Änderung 2",
                        verbose_name="Änderungsprotokoll",
                    ),
                ),
                (
                    "is_forced",
                    models.BooleanField(
                        default=False,
                        help_text="Nutzer müssen diese Version installieren",
                        verbose_name="Erzwungenes Update",
                    ),
                ),
                (
                    "min_required_version",
                    models.CharField(
                        blank=True,
                        help_text="Nutzer mit älteren Versionen müssen updaten",
                        max_length=20,
                        verbose_name="Mindestversion",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")),
            ],
            options={
                "verbose_name": "App-Version",
                "verbose_name_plural": "App-Versionen",
                "ordering": ["-release_date"],
                "unique_together": {("platform", "version")},
            },
        ),
    ]
