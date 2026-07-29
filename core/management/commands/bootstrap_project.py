from django.core.management.base import BaseCommand

from core.models import Station


class Command(BaseCommand):
    help = "Legt die konfigurierte Standardwache an."

    def handle(self, *args, **options):
        station = Station.get_default()
        self.stdout.write(self.style.SUCCESS(f"Standardwache {station.name} ist eingerichtet."))
