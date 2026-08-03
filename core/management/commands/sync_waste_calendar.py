import time

from django.core.management.base import BaseCommand

from core.models import Station
from core.waste_sync import WasteSyncError, sync_station_waste


class Command(BaseCommand):
    help = "Importiert Müllkalender (ICS) pro aktivierter Station."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=900)

    def handle(self, *args, **options):
        while True:
            for station in Station.objects.filter(
                is_active=True, waste_calendar_enabled=True
            ).exclude(waste_calendar_url=""):
                try:
                    count = sync_station_waste(station)
                    self.stdout.write(f"{station.slug}: {count} Abfuhren")
                except WasteSyncError as exc:
                    self.stderr.write(f"{station.slug}: {exc}")
                except Exception as exc:
                    self.stderr.write(f"{station.slug}: Unerwarteter Fehler: {exc}")
            if not options["watch"]:
                break
            time.sleep(max(options["interval"], 60))
