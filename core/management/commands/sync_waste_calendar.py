from django.core.management.base import BaseCommand

from core.models import Station
from core.waste_sync import sync_station_waste


class Command(BaseCommand):
    help = "Importiert die stationsspezifischen Muellkalender-ICS-Quellen."

    def handle(self, *args, **options):
        stations = Station.objects.filter(
            waste_calendar_enabled=True, is_active=True
        ).exclude(waste_calendar_url="")
        if not stations:
            self.stdout.write("Keine aktiven Muellkalender-Quellen konfiguriert.")
            return
        for station in stations:
            try:
                count = sync_station_waste(station)
                self.stdout.write(f"{station.name}: {count} Abfuhrtermine")
            except Exception as exc:  # noqa: BLE001 - isolate one external source
                self.stderr.write(f"{station.name}: {exc}")
