from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .models import Station


class DataProtectionOfficer(models.Model):
    """Stationsbezogener Datenschutzkontakt für Betrieb und Art.-13-Informationen.

    Die Kontaktdaten werden ausschließlich durch Administratoren gepflegt. Nur
    Datensätze mit ``publish_in_privacy_notice=True`` dürfen auf der öffentlichen
    Datenschutzseite erscheinen; interne Notizen werden niemals ausgegeben.
    """

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="data_protection_officers",
        verbose_name="Wache",
    )
    display_name = models.CharField(
        max_length=160,
        verbose_name="Name / Bezeichnung",
        help_text="Person oder Funktionsbezeichnung, z. B. Datenschutzbeauftragte/r.",
    )
    organization = models.CharField(
        max_length=180,
        blank=True,
        default="",
        verbose_name="Organisation / externer Dienstleister",
    )
    email = models.EmailField(verbose_name="E-Mail")
    phone = models.CharField(max_length=60, blank=True, default="", verbose_name="Telefon")
    postal_address = models.TextField(
        max_length=600,
        blank=True,
        default="",
        verbose_name="Postanschrift",
    )
    is_external = models.BooleanField(default=False, verbose_name="Extern bestellt")
    is_primary = models.BooleanField(default=False, verbose_name="Hauptkontakt")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    publish_in_privacy_notice = models.BooleanField(
        default=True,
        verbose_name="Auf Datenschutzseite veröffentlichen",
        help_text=(
            "Veröffentlicht nur die Kontaktfelder dieses Datensatzes. "
            "Interne Notizen bleiben immer nichtöffentlich."
        ),
    )
    internal_notes = models.TextField(
        max_length=1200,
        blank=True,
        default="",
        verbose_name="Interne Notiz",
        help_text="Nur im Django-Admin sichtbar; nicht für öffentliche Inhalte verwenden.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Datenschutzbeauftragte/r"
        verbose_name_plural = "Datenschutzbeauftragte"
        ordering = ["station", "-is_primary", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["station"],
                condition=Q(is_primary=True, is_active=True),
                name="unique_active_primary_dpo_per_station",
            ),
        ]
        indexes = [
            models.Index(
                fields=["station", "is_active", "publish_in_privacy_notice"],
                name="dpo_station_public_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.is_primary and self.is_active and self.station_id:
            existing = type(self).objects.filter(
                station_id=self.station_id,
                is_primary=True,
                is_active=True,
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    {"is_primary": "Pro Wache darf nur ein aktiver Hauptkontakt hinterlegt sein."}
                )
        if self.publish_in_privacy_notice and not self.is_active:
            raise ValidationError(
                {
                    "publish_in_privacy_notice": (
                        "Nur aktive Datenschutzkontakte können veröffentlicht werden."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.station}: {self.display_name}"
