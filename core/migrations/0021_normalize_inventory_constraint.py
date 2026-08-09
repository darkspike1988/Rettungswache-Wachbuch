from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_merge_0019_branches"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="inventoryitem",
            name="inventory_holder_time_match",
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(holder__isnull=True) & models.Q(checked_out_at__isnull=True))
                    | (models.Q(holder__isnull=False) & models.Q(checked_out_at__isnull=False))
                ),
                name="inventory_holder_time_match",
            ),
        ),
    ]
