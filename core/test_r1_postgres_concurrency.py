import queue
import threading
import unittest

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import connection, connections, transaction
from django.db.utils import OperationalError
from django.test import TransactionTestCase

from core.models import AuditEvent, HandoverEntry, HandoverRevision, Membership, Station
from core.services import (
    StaleHandoverRevision,
    acknowledge_handover,
    change_handover_status,
    update_handover_content,
)
from core.wachalltag_models import HandoverAck


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "R1-Rowlock-Nachweis nur auf PostgreSQL aussagekraeftig: SQLite kennt keine "
    "Zeilensperren und wuerde nur einen Backend-Fehler statt der Sperrsemantik zeigen.",
)
class HandoverConcurrencyPostgresTest(TransactionTestCase):
    # Django-Idiom: Set der vom Test beruehrten DB-Aliase (bewusst mutabel).
    databases = {"default"}  # noqa: RUF012
    requires_postgres_evidence = True

    def setUp(self):
        super().setUp()
        self._worker_pids = []
        self.station = Station.objects.create(name="Wache A", slug="wache-a")
        self.user1 = User.objects.create_user(username="user1", password="pw")
        self.membership1 = Membership.objects.create(
            user=self.user1, station=self.station, role=Membership.Role.MEMBER
        )
        self.user2 = User.objects.create_user(username="user2", password="pw")
        self.membership2 = Membership.objects.create(
            user=self.user2, station=self.station, role=Membership.Role.MEMBER
        )

    def _run_in_thread(self, target, *args, **kwargs):
        def wrapper(q_out):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid = cursor.fetchone()[0]
                res = target(*args, **kwargs)
                q_out.put(("backend_pid", backend_pid))
                q_out.put(("success", res))
            except Exception as e:  # noqa: BLE001 - Workerfehler an den Test weiterreichen
                q_out.put(("exception", e))
            finally:
                connections.close_all()

        q = queue.Queue()
        t = threading.Thread(target=wrapper, args=(q,), daemon=True)
        t.start()
        return t, q

    def _collect(self, thread, q, name):
        """Warte bounded auf einen Worker-Thread und liefere sein Ergebnis.

        Kein Rennsteuerungs-Sleep: Join-/Queue-Timeouts dienen nur als
        Abbruchschutz, damit ein haengender Thread den Lauf nie blockiert.
        """
        thread.join(timeout=15)
        if thread.is_alive():
            raise AssertionError(f"Worker '{name}' haengt noch nach 15s.")
        try:
            first = q.get(timeout=1)
            if first[0] == "backend_pid":
                self._worker_pids.append(first[1])
                return q.get(timeout=1)
            return first
        except queue.Empty:
            raise AssertionError(f"Worker '{name}' lieferte kein Ergebnis.")

    def _create_handover(self, title):
        handover = HandoverEntry.objects.create(
            station=self.station,
            category=HandoverEntry.Category.MATERIAL,
            priority=HandoverEntry.Priority.NORMAL,
            status=HandoverEntry.Status.OPEN,
            title=title,
            details="Details",
            author=self.user1,
            version=1,
        )
        HandoverRevision.objects.create(
            handover=handover,
            version=1,
            snapshot={
                "category": handover.category,
                "priority": handover.priority,
                "status": handover.status,
                "title": handover.title,
                "details": handover.details,
            },
            changed_by=self.user1,
        )
        return handover

    def test_same_ack_parallel_is_idempotent(self):
        handover = self._create_handover("test_idempotent")
        barrier = threading.Barrier(2)

        def ack_thread():
            barrier.wait(timeout=5)
            return acknowledge_handover(handover, self.membership1, 1)

        t1, q1 = self._run_in_thread(ack_thread)
        t2, q2 = self._run_in_thread(ack_thread)

        res1_type, res1_val = self._collect(t1, q1, "ack-parallel-1")
        res2_type, res2_val = self._collect(t2, q2, "ack-parallel-2")

        if res1_type == "exception":
            raise res1_val
        if res2_type == "exception":
            raise res2_val

        created_flags = [res1_val[1], res2_val[1]]
        self.assertIn(True, created_flags)
        self.assertIn(False, created_flags)

        self.assertEqual(len(set(self._worker_pids)), 2)
        self.assertEqual(res1_val[0].pk, res2_val[0].pk)
        self.assertEqual(HandoverAck.objects.filter(handover=handover).count(), 1)
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.acknowledged", object_id=str(handover.pk)
            ).count(),
            1,
        )

    def test_change_and_ack_both_orders(self):
        # 1. ack-vor-change
        h1 = self._create_handover("H1")
        ack_done = threading.Event()
        change_done = threading.Event()

        def ack_before_change():
            acknowledge_handover(h1, self.membership1, 1)
            ack_done.set()
            self.assertTrue(change_done.wait(timeout=5), "change did not commit")
            try:
                acknowledge_handover(h1, self.membership1, 1)
                return "success"
            except StaleHandoverRevision:
                return "stale"

        def change_after_ack():
            self.assertTrue(ack_done.wait(timeout=5), "ack did not commit")
            update_handover_content(h1, {"title": "H1_neu"}, self.membership2)
            change_done.set()

        t1, q1 = self._run_in_thread(ack_before_change)
        t2, q2 = self._run_in_thread(change_after_ack)
        r1_type, r1_val = self._collect(t1, q1, "ack-before-change")
        r2_type, r2_val = self._collect(t2, q2, "change-after-ack")
        if r1_type == "exception":
            raise r1_val
        if r2_type == "exception":
            raise r2_val

        self.assertEqual(r1_val, "stale")
        self.assertEqual(r2_val, None)

        self.assertEqual(HandoverAck.objects.filter(handover=h1).count(), 1)
        self.assertEqual(HandoverAck.objects.get(handover=h1).version, 1)
        self.assertEqual(HandoverRevision.objects.filter(handover=h1).count(), 2)

        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.acknowledged", object_id=str(h1.pk)
            ).count(),
            1,
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.content_updated", object_id=str(h1.pk)
            ).count(),
            1,
        )

        # 2. change-vor-ack
        h2 = self._create_handover("H2")
        change2_done = threading.Event()

        def change_before_ack():
            update_handover_content(h2, {"title": "H2_neu"}, self.membership2)
            change2_done.set()

        def ack_after_change():
            self.assertTrue(change2_done.wait(timeout=5), "change did not commit")
            try:
                acknowledge_handover(h2, self.membership1, 1)
                return "success"
            except StaleHandoverRevision:
                return "stale"

        t3, q3 = self._run_in_thread(change_before_ack)
        t4, q4 = self._run_in_thread(ack_after_change)
        r3_type, r3_val = self._collect(t3, q3, "change-before-ack")
        r4_type, r4_val = self._collect(t4, q4, "ack-after-change")
        if r3_type == "exception":
            raise r3_val
        if r4_type == "exception":
            raise r4_val

        self.assertEqual(r3_val, None)
        self.assertEqual(r4_val, "stale")

        self.assertEqual(HandoverAck.objects.filter(handover=h2).count(), 0)
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.acknowledged", object_id=str(h2.pk)
            ).count(),
            0,
        )

    def test_concurrent_ack_vs_change_invariant(self):
        handover = self._create_handover("HC")
        barrier = threading.Barrier(2)

        def ack_thread():
            barrier.wait(timeout=5)
            try:
                acknowledge_handover(handover, self.membership1, 1)
                return "success"
            except StaleHandoverRevision:
                return "stale"

        def change_thread():
            barrier.wait(timeout=5)
            update_handover_content(handover, {"title": "HC_neu"}, self.membership2)
            return "success"

        t1, q1 = self._run_in_thread(ack_thread)
        t2, q2 = self._run_in_thread(change_thread)

        r1_type, r1_val = self._collect(t1, q1, "ack-race")
        r2_type, r2_val = self._collect(t2, q2, "change-race")
        if r1_type == "exception":
            raise r1_val
        if r2_type == "exception":
            raise r2_val

        handover.refresh_from_db()
        self.assertEqual(handover.version, 2)

        ack_count = HandoverAck.objects.filter(handover=handover).count()
        self.assertIn(r1_val, ["success", "stale"])
        self.assertEqual(r2_val, "success")
        self.assertEqual(ack_count, 1 if r1_val == "success" else 0)

        audit_ack_count = AuditEvent.objects.filter(
            action="handover.acknowledged", object_id=str(handover.pk)
        ).count()
        self.assertEqual(audit_ack_count, ack_count)

        if ack_count == 1:
            self.assertEqual(HandoverAck.objects.get(handover=handover).version, 1)
            self.assertEqual(audit_ack_count, 1)

        audit_change_count = AuditEvent.objects.filter(
            action="handover.content_updated", object_id=str(handover.pk)
        ).count()
        self.assertEqual(audit_change_count, 1)

        rev_count = HandoverRevision.objects.filter(handover=handover).count()
        self.assertEqual(rev_count, 2)

    def _parallel_results(self, first, second):
        barrier = threading.Barrier(2)

        def start(fn):
            barrier.wait(timeout=5)
            return fn()

        workers = [self._run_in_thread(start, fn) for fn in (first, second)]
        results = [
            self._collect(t, q, f"worker-{i}") for i, (t, q) in enumerate(workers)
        ]
        for kind, value in results:
            if kind == "exception":
                raise value
        self.assertEqual(len(set(self._worker_pids[-2:])), 2)
        return [value for _, value in results]

    def test_real_row_lock_nowait_conflicts(self):
        handover = self._create_handover("rowlock")
        held, release = threading.Event(), threading.Event()

        def holder():
            with transaction.atomic():
                HandoverEntry.objects.select_for_update().get(pk=handover.pk)
                held.set()
                self.assertTrue(
                    release.wait(timeout=5), "lock release was not signalled"
                )

        worker, result = self._run_in_thread(holder)
        try:
            self.assertTrue(held.wait(timeout=5), "holder did not acquire lock")
            with self.assertRaises(OperationalError) as raised:
                with transaction.atomic():
                    HandoverEntry.objects.select_for_update(nowait=True).get(
                        pk=handover.pk
                    )
            self.assertEqual(raised.exception.__cause__.sqlstate, "55P03")
        finally:
            release.set()
            kind, value = self._collect(worker, result, "rowlock-holder")
            if kind == "exception":
                raise value

    def test_two_content_changes_preserve_both_revisions(self):
        handover = self._create_handover("content")
        versions = self._parallel_results(
            lambda: (
                update_handover_content(
                    handover, {"title": "A"}, self.membership1
                ).version
            ),
            lambda: (
                update_handover_content(
                    handover, {"title": "B"}, self.membership2
                ).version
            ),
        )
        handover.refresh_from_db()
        revisions = list(
            HandoverRevision.objects.filter(handover=handover).order_by("version")
        )
        self.assertEqual(sorted(versions), [2, 3])
        self.assertEqual(handover.version, 3)
        self.assertEqual([r.version for r in revisions], [1, 2, 3])
        self.assertEqual({r.snapshot["title"] for r in revisions[1:]}, {"A", "B"})
        self.assertEqual(handover.title, revisions[-1].snapshot["title"])
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.content_updated", object_id=str(handover.pk)
            ).count(),
            2,
        )

    def test_two_status_changes_preserve_both_revisions(self):
        handover = self._create_handover("status")
        versions = self._parallel_results(
            lambda: (
                change_handover_status(
                    handover, HandoverEntry.Status.DONE, self.membership1
                ).version
            ),
            lambda: (
                change_handover_status(
                    handover, HandoverEntry.Status.IN_PROGRESS, self.membership2
                ).version
            ),
        )
        handover.refresh_from_db()
        revisions = list(
            HandoverRevision.objects.filter(handover=handover).order_by("version")
        )
        self.assertEqual(sorted(versions), [2, 3])
        self.assertEqual(handover.version, 3)
        self.assertEqual([r.version for r in revisions], [1, 2, 3])
        self.assertEqual(
            {r.snapshot["status"] for r in revisions[1:]},
            {HandoverEntry.Status.DONE, HandoverEntry.Status.IN_PROGRESS},
        )
        self.assertEqual(handover.status, revisions[-1].snapshot["status"])
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.status_changed", object_id=str(handover.pk)
            ).count(),
            2,
        )

    def test_two_users_can_ack_same_revision_independently(self):
        handover = self._create_handover("users")
        results = self._parallel_results(
            lambda: acknowledge_handover(handover, self.membership1, 1),
            lambda: acknowledge_handover(handover, self.membership2, 1),
        )
        self.assertEqual([created for _, created in results], [True, True])
        self.assertEqual(
            set(
                HandoverAck.objects.filter(handover=handover).values_list(
                    "user_id", "version"
                )
            ),
            {(self.user1.pk, 1), (self.user2.pk, 1)},
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.acknowledged", object_id=str(handover.pk)
            ).count(),
            2,
        )

    def test_foreign_station_denied_on_pg(self):
        other_station = Station.objects.create(name="Wache B", slug="wache-b")
        other_user = User.objects.create_user(username="other", password="pw")
        other_membership = Membership.objects.create(
            user=other_user, station=other_station, role=Membership.Role.MEMBER
        )

        handover = self._create_handover("HF")

        def ack_thread():
            acknowledge_handover(handover, other_membership, 1)

        t1, q1 = self._run_in_thread(ack_thread)

        res_type, res_val = self._collect(t1, q1, "foreign-station-ack")
        self.assertEqual(res_type, "exception")
        self.assertIsInstance(res_val, PermissionDenied)

        self.assertEqual(HandoverAck.objects.filter(handover=handover).count(), 0)
        self.assertEqual(
            AuditEvent.objects.filter(
                action="handover.acknowledged", object_id=str(handover.pk)
            ).count(),
            0,
        )
