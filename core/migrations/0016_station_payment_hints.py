from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_station_checklists"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="paypal_me_url",
            field=models.URLField(blank=True, default="", verbose_name="PayPal.me-Link"),
        ),
        migrations.AddField(
            model_name="station",
            name="wero_link",
            field=models.URLField(blank=True, default="", verbose_name="Wero-Link"),
        ),
        migrations.AddField(
            model_name="station",
            name="iban",
            field=models.CharField(blank=True, default="", max_length=34, verbose_name="IBAN"),
        ),
        migrations.AddField(
            model_name="station",
            name="bic",
            field=models.CharField(blank=True, default="", max_length=12, verbose_name="BIC"),
        ),
        migrations.AddField(
            model_name="station",
            name="payment_note",
            field=models.TextField(blank=True, default="", verbose_name="Zahlungshinweis"),
        ),
    ]
