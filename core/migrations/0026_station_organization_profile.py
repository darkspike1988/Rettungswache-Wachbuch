from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0025_chatgroup_groupmessage_chatgroupmember"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="organization_profile",
            field=models.CharField(
                choices=[
                    ("rescue", "Rettungsdienst"),
                    ("fire", "Feuerwehr"),
                    ("police", "Polizei"),
                    ("general", "Allgemein"),
                ],
                default="rescue",
                max_length=20,
                verbose_name="Organisationsprofil",
            ),
        ),
    ]
