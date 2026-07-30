from django.db import migrations


def disable_feeds_for_existing_stations(apps, schema_editor):
    """Migration 0003 set feeds_enabled=True for existing rows via AddField default.

    The intended product default is opt-in. Existing stations are reset here;
    operators who want external feeds must re-enable them under /einstellungen/.
    """
    Station = apps.get_model("core", "Station")
    Station.objects.filter(feeds_enabled=True).update(feeds_enabled=False)


class Migration(migrations.Migration):
    dependencies = [("core", "0003_station_module_settings")]

    operations = [
        migrations.RunPython(disable_feeds_for_existing_stations, migrations.RunPython.noop),
    ]
