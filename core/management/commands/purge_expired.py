from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import AuditEvent, CalendarEvent, HandoverEntry, Station
from core.services import audit


class Command(BaseCommand):
    help = (
        "Loescht Daten nach den je Wache eingestellten Fristen. Kassenbuchungen "
        "bleiben ausgenommen. Benoetigt die Datenbank-Owner-Rolle, weil Audit "
        "und Revisionen fuer das Anwendungskonto schreibgeschuetzt sind."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur berichten, was geloescht wuerde.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        total = 0

        for station in Station.objects.all():
            plan = {}

            if station.retention_handover_days:
                cutoff = now - timedelta(days=station.retention_handover_days)
                plan["erledigte Uebergaben"] = HandoverEntry.objects.filter(
                    station=station,
                    status=HandoverEntry.Status.DONE,
                    completed_at__lt=cutoff,
                )
            if station.retention_calendar_days:
                cutoff = now - timedelta(days=station.retention_calendar_days)
                plan["Termine"] = CalendarEvent.objects.filter(
                    station=station, ends_at__lt=cutoff,
                )
            if station.retention_audit_days:
                cutoff = now - timedelta(days=station.retention_audit_days)
                plan["Audit-Ereignisse"] = AuditEvent.objects.filter(
                    station=station, created_at__lt=cutoff,
                )

            if not plan:
                self.stdout.write(f"{station.name}: keine Frist gesetzt, nichts zu tun.")
                continue

            counts = {label: queryset.count() for label, queryset in plan.items()}
            summary = ", ".join(f"{count} {label}" for label, count in counts.items())
            affected = sum(counts.values())

            if dry_run:
                self.stdout.write(f"{station.name}: wuerde loeschen - {summary}.")
                continue

            if affected:
                with transaction.atomic():
                    for queryset in plan.values():
                        # Bewusst ueber das Queryset: die Modelle sperren
                        # Einzelloeschungen, die Aufbewahrungsfrist ist aber
                        # eine bewusste Entscheidung der verantwortlichen Stelle.
                        queryset.delete()
                    audit(None, station, "retention.purged", station, {"counts": counts})
                total += affected
            self.stdout.write(f"{station.name}: geloescht - {summary}.")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Fertig, {total} Datensaetze geloescht."))
