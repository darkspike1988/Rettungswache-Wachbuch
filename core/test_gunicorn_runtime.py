from pathlib import Path

from django.test import SimpleTestCase


class GunicornRuntimeContractTests(SimpleTestCase):
    def test_read_only_runtime_disables_home_control_socket(self):
        start_script = (
            Path(__file__).resolve().parent.parent / "scripts" / "start-web.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--no-control-socket", start_script)
