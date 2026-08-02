from django.core.management.base import BaseCommand

from core.models import Station
from core.task_board import ensure_default_station_tasks


class Command(BaseCommand):
    help = "Legt die konfigurierte Standardwache und Tagesaufgaben-Vorlage an."

    def handle(self, *args, **options):
        station = Station.get_default()
        created = ensure_default_station_tasks(station)
        self.stdout.write(self.style.SUCCESS(f"Standardwache {station.name} ist eingerichtet."))
        if created:
            self.stdout.write(self.style.SUCCESS(f"{created} Tagesaufgaben aus der Wandvorlage angelegt."))
