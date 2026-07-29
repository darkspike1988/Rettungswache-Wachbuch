from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import (
    BirthdayPreference,
    CalendarEvent,
    CoffeeEntry,
    DailyTeamNote,
    HandoverEntry,
    HandoverRevision,
    Membership,
    Station,
)
from core.services import handover_snapshot

# Erfundene Personen und Vorgaenge - bewusst ohne Patienten- oder Einsatzbezug.
DEMO_PEOPLE = [
    ("demo-mara@wachbuch.invalid", "Mara", Membership.Role.SHIFT_LEAD),
    ("demo-jonas@wachbuch.invalid", "Jonas", Membership.Role.MEMBER),
    ("demo-sena@wachbuch.invalid", "Sena", Membership.Role.CASHIER),
]

DEMO_HANDOVERS = [
    ("Sauerstoffflasche RTW 2 fast leer", "vehicle", "urgent", "open",
     "Fuellstand unter 50 bar. Ersatzflasche steht bereit, Tausch noch offen.", 0),
    ("Absturzsicherung Halle geprueft", "safety", "important", "in_progress",
     "Pruefplakette fehlt. Rueckmeldung der Technik steht aus.", None),
    ("Verbandskaesten eingetroffen", "material", "normal", "done",
     "Lieferung kontrolliert und eingeraeumt.", -1),
    ("Fahrzeugcheck RTW 1", "vehicle", "normal", "done",
     "Taeglicher Check ohne Beanstandung.", 0),
    ("Kaffeemaschine entkalken", "station", "normal", "open",
     "Entkalker liegt im Schrank ueber der Spuele.", 1),
    ("Waschmaschine macht Geraeusche", "station", "important", "open",
     "Hausmeister ist informiert, Termin noch offen.", None),
]

DEMO_TEAMS = {0: "Mara / Jonas", -1: "Sena / Mara", 1: "Jonas / Sena"}


class Command(BaseCommand):
    help = (
        "Legt die Demowache mit erfundenen Beispieldaten an oder setzt sie "
        "zurueck. Nur fuer Schaufenster-Instanzen mit DEMO_MODE=true."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Vorhandene Demodaten vorher loeschen.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = settings.DEMO_STATION_SLUG
        if not slug:
            raise CommandError("DEMO_STATION_SLUG ist nicht gesetzt.")

        if options["reset"]:
            self._reset(slug)

        station, _ = Station.objects.get_or_create(
            slug=slug,
            defaults={
                "name": "Rettungswache Demo",
                "location": "Musterstadt",
                "city": "Musterstadt",
                "onboarded": True,
                "feeds_enabled": False,
            },
        )
        station.name = "Rettungswache Demo"
        station.location = "Musterstadt"
        station.onboarded = True
        station.coffee_paypal_link = "https://paypal.me/beispielwache"
        station.coffee_account_holder = "Foerderverein Rettungswache Demo"
        station.coffee_iban = "DE89370400440532013000"
        station.save()

        people = [self._person(*entry, station=station) for entry in DEMO_PEOPLE]
        visitor = self._visitor(station)
        self._handovers(station, people)
        self._teams(station, people[0])
        self._calendar(station, people[0])
        self._coffee(station, people, visitor)
        self._birthday(station, people[1])

        self.stdout.write(self.style.SUCCESS(
            f"Demowache '{station.name}' ist bereit. Demokonto: {visitor.username}"
        ))

    def _reset(self, slug):
        station = Station.objects.filter(slug=slug).first()
        if station is None:
            return
        HandoverEntry.objects.filter(station=station).delete()
        DailyTeamNote.objects.filter(station=station).delete()
        CalendarEvent.objects.filter(station=station).delete()
        BirthdayPreference.objects.filter(station=station).delete()
        # Kassenbuchungen sperren sich gegen Einzelloeschung; im Demobestand
        # ist das Zuruecksetzen aber ausdruecklich gewollt.
        CoffeeEntry.objects.filter(station=station).delete()
        self.stdout.write("Bisherige Demodaten entfernt.")

    def _person(self, username, first_name, role, station):
        user, created = User.objects.get_or_create(
            username=username, defaults={"first_name": first_name, "email": username},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        Membership.objects.get_or_create(
            user=user, station=station, defaults={"role": role},
        )
        return user

    def _visitor(self, station):
        """Das Konto, mit dem Besucher die Demo ansehen. Ohne nutzbares
        Passwort - der Zugang laeuft ausschliesslich ueber die Demoseite."""
        user, created = User.objects.get_or_create(
            username=settings.DEMO_USERNAME,
            defaults={"first_name": "Gast", "email": settings.DEMO_USERNAME},
        )
        if created or user.has_usable_password():
            user.set_unusable_password()
            user.save(update_fields=["password"])
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        Membership.objects.update_or_create(
            user=user, station=station,
            defaults={"role": Membership.Role.MEMBER, "is_active": True},
        )
        return user

    def _handovers(self, station, people):
        today = timezone.localdate()
        for index, (title, category, priority, status, details, day_offset) in enumerate(
            DEMO_HANDOVERS
        ):
            author = people[index % len(people)]
            entry = HandoverEntry.objects.create(
                station=station,
                category=category,
                priority=priority,
                status=status,
                title=title,
                details=details,
                author=author,
                for_date=today + timedelta(days=day_offset) if day_offset is not None else None,
                completed_at=timezone.now() if status == "done" else None,
            )
            HandoverRevision.objects.create(
                handover=entry, version=1,
                snapshot=handover_snapshot(entry), changed_by=author,
            )

    def _teams(self, station, author):
        today = timezone.localdate()
        for offset, note in DEMO_TEAMS.items():
            DailyTeamNote.objects.update_or_create(
                station=station, date=today + timedelta(days=offset),
                defaults={"note": note, "updated_by": author},
            )

    def _calendar(self, station, author):
        now = timezone.now()
        for title, description, days, hours in [
            ("Gefahrgut-Uebung", "Jaehrliche Pflichtuebung, bitte puenktlich.", 3, 3),
            ("Teamsitzung", "Kurze Besprechung offener Punkte.", 9, 1),
        ]:
            starts = now + timedelta(days=days)
            CalendarEvent.objects.get_or_create(
                station=station, title=title,
                defaults={
                    "description": description,
                    "starts_at": starts,
                    "ends_at": starts + timedelta(hours=hours),
                    "created_by": author,
                },
            )

    def _coffee(self, station, people, visitor):
        cashier = people[2]
        for member, amount, reason in [
            (people[0], 1000, "Einzahlung"),
            (people[1], 500, "Einzahlung"),
            (visitor, 750, "Einzahlung"),
            (people[0], -320, "Kaffeebohnen nachgekauft"),
        ]:
            CoffeeEntry.objects.create(
                station=station, member=member, amount_cents=amount,
                reason=reason, created_by=cashier,
            )

    def _birthday(self, station, user):
        BirthdayPreference.objects.update_or_create(
            user=user, station=station,
            defaults={
                "day": 14, "month": 8, "is_visible": True,
                "consented_at": timezone.now(),
            },
        )
