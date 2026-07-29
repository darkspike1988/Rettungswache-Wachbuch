from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Membership, Station


class Command(BaseCommand):
    help = "Gibt einem vorhandenen Benutzer die Verwaltung der Standardwache frei."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--station", default=settings.DEFAULT_STATION_SLUG)

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("Der Benutzer existiert nicht.") from exc
        if options["station"] == settings.DEFAULT_STATION_SLUG:
            station = Station.get_default()
        else:
            try:
                station = Station.objects.get(slug=options["station"])
            except Station.DoesNotExist as exc:
                raise CommandError("Die angegebene Wache existiert nicht.") from exc
        other_membership = Membership.objects.filter(user=user, is_active=True).exclude(
            station=station
        ).first()
        if other_membership:
            raise CommandError("Der Benutzer hat bereits Zugang zu einer anderen Wache.")
        Membership.objects.update_or_create(
            user=user,
            station=station,
            defaults={"role": Membership.Role.ADMIN, "is_active": True},
        )
        self.stdout.write(self.style.SUCCESS(f"{user.username} verwaltet jetzt {station.name}."))
