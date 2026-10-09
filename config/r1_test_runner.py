"""Fail-closed evidence runner: empty, non-PG or skipped R1 suites are not green."""

import unittest

from django.db import connection
from django.test.runner import DiscoverRunner


def _tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _tests(item)
        else:
            yield item


class PostgresEvidenceRunner(DiscoverRunner):
    def run_suite(self, suite, **kwargs):
        if connection.vendor != "postgresql":
            raise RuntimeError("R1 evidence requires PostgreSQL, not SQLite.")
        required = [
            t for t in _tests(suite) if getattr(t, "requires_postgres_evidence", False)
        ]
        if not required:
            raise RuntimeError(
                "R1 evidence suite contains no required concurrency tests."
            )
        result = super().run_suite(suite, **kwargs)
        if any(
            getattr(t, "requires_postgres_evidence", False) for t, _ in result.skipped
        ):
            raise RuntimeError("A required PostgreSQL evidence test was skipped.")
        return result
