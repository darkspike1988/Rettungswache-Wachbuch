import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import UpdateRequest
from core.services import audit


class Command(BaseCommand):
    help = "Claims or finishes host-side update requests using machine-readable JSON."

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument("--claim", action="store_true")
        action.add_argument("--finish", type=int, metavar="ID")
        parser.add_argument("--status", choices=["succeeded", "failed"])
        parser.add_argument("--message", default="")

    def handle(self, *args, **options):
        if options["claim"]:
            with transaction.atomic():
                update = (
                    UpdateRequest.objects.select_for_update(skip_locked=True)
                    .filter(status=UpdateRequest.Status.PENDING)
                    .order_by("requested_at")
                    .first()
                )
                if update is None:
                    self.stdout.write(json.dumps({"ok": True, "request": None}))
                    return
                update.status = UpdateRequest.Status.RUNNING
                update.started_at = timezone.now()
                update.result_message = "Update-Runner wurde manuell gestartet."
                update.save(update_fields=["status", "started_at", "result_message"])
            self.stdout.write(
                json.dumps(
                    {
                        "ok": True,
                        "request": {
                            "id": update.pk,
                            "current_version": update.current_version,
                            "target_version": update.target_version,
                            "release_url": update.release_url,
                        },
                    }
                )
            )
            return

        if not options["status"]:
            raise CommandError("--finish erfordert --status.")
        update = UpdateRequest.objects.filter(pk=options["finish"]).first()
        if update is None:
            raise CommandError("Updateauftrag wurde nicht gefunden.")
        if update.status != UpdateRequest.Status.RUNNING:
            raise CommandError(
                "Nur laufende Updateaufträge können abgeschlossen werden."
            )
        update.status = options["status"]
        update.finished_at = timezone.now()
        update.result_message = str(options["message"] or "")[:500]
        update.save(update_fields=["status", "finished_at", "result_message"])
        audit(
            update.requested_by,
            update.station,
            f"system.update_{update.status}",
            update,
            {
                "current_version": update.current_version,
                "target_version": update.target_version,
                "status": update.status,
            },
        )
        self.stdout.write(
            json.dumps({"ok": True, "request_id": update.pk, "status": update.status})
        )
