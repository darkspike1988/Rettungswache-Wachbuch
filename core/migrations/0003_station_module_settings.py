from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_coffeeentry_unique_coffee_correction_and_more")]

    operations = [
        migrations.AddField(
            model_name="station",
            name="birthdays_enabled",
            field=models.BooleanField(default=True, verbose_name="Geburtstage aktiviert"),
        ),
        migrations.AddField(
            model_name="station",
            name="calendar_enabled",
            field=models.BooleanField(default=True, verbose_name="Kalender aktiviert"),
        ),
        migrations.AddField(
            model_name="station",
            name="coffee_enabled",
            field=models.BooleanField(default=True, verbose_name="Kaffeekasse aktiviert"),
        ),
        migrations.AddField(
            model_name="station",
            name="feeds_enabled",
            field=models.BooleanField(default=True, verbose_name="Externe Meldungen aktiviert"),
        ),
        migrations.AlterField(
            model_name="station",
            name="feeds_enabled",
            field=models.BooleanField(default=False, verbose_name="Externe Meldungen aktiviert"),
        ),
    ]
