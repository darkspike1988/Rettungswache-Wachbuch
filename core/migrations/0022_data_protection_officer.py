from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_normalize_inventory_constraint"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataProtectionOfficer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(help_text="Person oder Funktionsbezeichnung, z. B. Datenschutzbeauftragte/r.", max_length=160, verbose_name="Name / Bezeichnung")),
                ("organization", models.CharField(blank=True, default="", max_length=180, verbose_name="Organisation / externer Dienstleister")),
                ("email", models.EmailField(max_length=254, verbose_name="E-Mail")),
                ("phone", models.CharField(blank=True, default="", max_length=60, verbose_name="Telefon")),
                ("postal_address", models.TextField(blank=True, default="", max_length=600, verbose_name="Postanschrift")),
                ("is_external", models.BooleanField(default=False, verbose_name="Extern bestellt")),
                ("is_primary", models.BooleanField(default=False, verbose_name="Hauptkontakt")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktiv")),
                ("publish_in_privacy_notice", models.BooleanField(default=True, help_text="Veröffentlicht nur die Kontaktfelder dieses Datensatzes. Interne Notizen bleiben immer nichtöffentlich.", verbose_name="Auf Datenschutzseite veröffentlichen")),
                ("internal_notes", models.TextField(blank=True, default="", help_text="Nur im Django-Admin sichtbar; nicht für öffentliche Inhalte verwenden.", max_length=1200, verbose_name="Interne Notiz")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="data_protection_officers", to="core.station", verbose_name="Wache")),
            ],
            options={
                "verbose_name": "Datenschutzbeauftragte/r",
                "verbose_name_plural": "Datenschutzbeauftragte",
                "ordering": ["station", "-is_primary", "display_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="dataprotectionofficer",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True), ("is_primary", True)),
                fields=("station",),
                name="unique_active_primary_dpo_per_station",
            ),
        ),
        migrations.AddIndex(
            model_name="dataprotectionofficer",
            index=models.Index(
                fields=["station", "is_active", "publish_in_privacy_notice"],
                name="dpo_station_public_idx",
            ),
        ),
    ]
