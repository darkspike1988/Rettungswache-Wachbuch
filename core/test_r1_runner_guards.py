"""Unit tests of the fail-closed evidence runner, not PostgreSQL evidence."""

import unittest
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test.runner import DiscoverRunner

from config.r1_test_runner import PostgresEvidenceRunner


class EvidenceRunnerGuardsTests(SimpleTestCase):
    def test_sqlite_is_not_postgres_evidence(self):
        with patch("config.r1_test_runner.connection.vendor", "sqlite"):
            with self.assertRaisesRegex(RuntimeError, "requires PostgreSQL"):
                PostgresEvidenceRunner().run_suite(unittest.TestSuite())

    def test_empty_suite_is_not_green(self):
        with patch("config.r1_test_runner.connection.vendor", "postgresql"):
            with self.assertRaisesRegex(RuntimeError, "no required"):
                PostgresEvidenceRunner().run_suite(unittest.TestSuite())

    def test_required_skipped_test_is_not_green(self):
        case = unittest.FunctionTestCase(lambda: None)
        case.requires_postgres_evidence = True
        result = unittest.TestResult()
        result.skipped.append((case, "unexpected skip"))
        with patch("config.r1_test_runner.connection.vendor", "postgresql"):
            with patch.object(DiscoverRunner, "run_suite", return_value=result):
                with self.assertRaisesRegex(RuntimeError, "was skipped"):
                    PostgresEvidenceRunner().run_suite(unittest.TestSuite([case]))

    def test_complete_required_result_is_preserved(self):
        case = unittest.FunctionTestCase(lambda: None)
        case.requires_postgres_evidence = True
        result = unittest.TestResult()
        result.testsRun = 1
        with patch("config.r1_test_runner.connection.vendor", "postgresql"):
            with patch.object(DiscoverRunner, "run_suite", return_value=result):
                self.assertIs(
                    PostgresEvidenceRunner().run_suite(unittest.TestSuite([case])),
                    result,
                )
