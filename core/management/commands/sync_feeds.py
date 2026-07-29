import time

from django.core.management.base import BaseCommand

from core.feed_sync import sync_source
from core.models import FeedSource


class Command(BaseCommand):
    help = "Importiert erlaubte offizielle RSS- und CSV-Quellen."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=900)

    def handle(self, *args, **options):
        while True:
            for source in FeedSource.objects.filter(is_enabled=True):
                try:
                    count = sync_source(source)
                    self.stdout.write(f"{source.name}: {count} Eintraege")
                except Exception as exc:
                    self.stderr.write(f"{source.name}: {exc}")
            if not options["watch"]:
                break
            time.sleep(max(options["interval"], 60))
