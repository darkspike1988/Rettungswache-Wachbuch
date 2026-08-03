"""Delete terminal (sent/discarded/failed) PushOutbox rows older than retention."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PushOutbox


class Command(BaseCommand):
    help = "Entfernt abgeschlossene PushOutbox-Eintraege nach Aufbewahrungsfrist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=PushOutbox.RETENTION_DAYS,
            help="Aufbewahrung in Tagen (Standard: %(default)s).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Nur zaehlen, nicht loeschen.",
        )

    def handle(self, *args, **options):
        days = max(int(options["days"]), 0)
        if days <= 0:
            self.stdout.write("cleanup_pushoutbox: Aufbewahrung 0 Tage, ueberspringe.")
            return
        cutoff = timezone.now() - timezone.timedelta(days=days)
        qs = PushOutbox.objects.filter(
            status__in=[
                PushOutbox.Status.SENT,
                PushOutbox.Status.DISCARDED,
                PushOutbox.Status.FAILED,
            ],
            created_at__lt=cutoff,
        )
        if options["dry_run"]:
            count = qs.count()
            self.stdout.write(self.style.WARNING(
                f"cleanup_pushoutbox (dry-run): {count} Eintraege wuerden entfernt."
            ))
            return
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"cleanup_pushoutbox: {deleted} Eintraege entfernt (aelter als {days} Tage)."
        ))
