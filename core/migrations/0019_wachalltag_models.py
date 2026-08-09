from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_merge_0017_branches"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Defect",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True, default="", max_length=3000)),
                ("asset_ref", models.CharField(blank=True, default="", max_length=160)),
                ("priority", models.CharField(choices=[("normal", "Normal"), ("important", "Wichtig"), ("urgent", "Dringend")], default="normal", max_length=20)),
                ("status", models.CharField(choices=[("open", "Offen"), ("in_progress", "In Bearbeitung"), ("waiting", "Wartend"), ("done", "Erledigt")], default="open", max_length=20)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("category", models.CharField(choices=[("vehicle", "Fahrzeug"), ("material", "Material"), ("safety", "Sicherheit"), ("facility", "Gebaeude"), ("key", "Schluessel"), ("device", "Geraet"), ("task", "Aufgabe")], default="task", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_station_defects", to=settings.AUTH_USER_MODEL)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="owned_station_defects", to=settings.AUTH_USER_MODEL)),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="defects", to="core.station")),
            ],
            options={"ordering": ["status", "-priority", "due_at", "-updated_at"]},
        ),
        migrations.CreateModel(
            name="StationAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.SlugField(max_length=64)),
                ("label", models.CharField(max_length=160)),
                ("kind", models.CharField(choices=[("vehicle", "Fahrzeug"), ("device", "Geraet"), ("key", "Schluessel")], default="device", max_length=20)),
                ("status", models.CharField(choices=[("ready", "Einsatzklar"), ("limited", "Eingeschraenkt"), ("oob", "Ausser Betrieb"), ("workshop", "Werkstatt")], default="ready", max_length=20)),
                ("note", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="station_assets", to="core.station")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="updated_station_assets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["kind", "label"]},
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_id", models.SlugField(max_length=64)),
                ("label", models.CharField(max_length=160)),
                ("kind", models.CharField(choices=[("key", "Schluessel"), ("device", "Geraet"), ("vehicle", "Fahrzeug")], default="device", max_length=20)),
                ("checked_out_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("holder", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="checked_out_station_items", to=settings.AUTH_USER_MODEL)),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_items", to="core.station")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="updated_inventory_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["kind", "label"]},
        ),
        migrations.CreateModel(
            name="ChecklistSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interval", models.CharField(choices=[("daily", "Taeglich"), ("weekly", "Woechentlich"), ("monthly", "Monatlich")], max_length=20)),
                ("due_next", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("checklist", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="schedule", to="core.checklist")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="checklist_schedules", to="core.station")),
            ],
            options={"ordering": ["due_next", "checklist_id"]},
        ),
        migrations.CreateModel(
            name="HandoverAck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("handover", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acknowledgements", to="core.handoverentry")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="handover_acks", to="core.station")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="handover_acknowledgements", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="DefectEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("created", "Angelegt"), ("updated", "Bearbeitet"), ("status", "Status"), ("attachment", "Anhang")], max_length=20)),
                ("from_status", models.CharField(blank=True, default="", max_length=20)),
                ("to_status", models.CharField(blank=True, default="", max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="defect_events", to=settings.AUTH_USER_MODEL)),
                ("defect", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="core.defect")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="defect_events", to="core.station")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DefectAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(max_length=180)),
                ("content_type", models.CharField(max_length=40)),
                ("data", models.BinaryField(editable=False)),
                ("size", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("defect", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attachments", to="core.defect")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="defect_attachments", to="core.station")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="defect_attachments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AssetEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(blank=True, default="", max_length=20)),
                ("to_status", models.CharField(max_length=20)),
                ("note", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asset_events", to=settings.AUTH_USER_MODEL)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="core.stationasset")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asset_events", to="core.station")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="InventoryEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("checkout", "Ausgabe"), ("checkin", "Rueckgabe")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_events", to=settings.AUTH_USER_MODEL)),
                ("holder", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_event_holdings", to=settings.AUTH_USER_MODEL)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="core.inventoryitem")),
                ("station", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_events", to="core.station")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="stationasset",
            constraint=models.UniqueConstraint(fields=("station", "asset_id"), name="unique_station_asset_id"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(fields=("station", "item_id"), name="unique_station_inventory_id"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(condition=(models.Q(("checked_out_at__isnull", True), ("holder__isnull", True)) | models.Q(("checked_out_at__isnull", False), ("holder__isnull", False))), name="inventory_holder_time_match"),
        ),
        migrations.AddConstraint(
            model_name="handoverack",
            constraint=models.UniqueConstraint(fields=("handover", "user"), name="unique_handover_user_ack"),
        ),
        migrations.AddIndex(
            model_name="defect",
            index=models.Index(fields=["station", "status", "due_at"], name="defect_station_status_idx"),
        ),
        migrations.AddIndex(
            model_name="defect",
            index=models.Index(fields=["station", "priority"], name="defect_station_prio_idx"),
        ),
        migrations.AddIndex(
            model_name="stationasset",
            index=models.Index(fields=["station", "status"], name="asset_station_status_idx"),
        ),
        migrations.AddIndex(
            model_name="handoverack",
            index=models.Index(fields=["station", "handover"], name="ack_station_handover_idx"),
        ),
        migrations.AddIndex(
            model_name="defectevent",
            index=models.Index(fields=["station", "-created_at"], name="defect_event_station_idx"),
        ),
        migrations.AddIndex(
            model_name="defectattachment",
            index=models.Index(fields=["station", "defect"], name="attachment_station_def_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryevent",
            index=models.Index(fields=["station", "-created_at"], name="inventory_event_station_idx"),
        ),
    ]
