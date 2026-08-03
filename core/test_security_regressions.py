from pathlib import Path

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from .middleware import SecurityHeadersMiddleware


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TemplateSecurityRegressionTests(SimpleTestCase):
    json_templates = (
        "templates/core/chat.html",
        "templates/core/private_chat_thread.html",
        "templates/core/secure_mail_inbox.html",
        "templates/core/secure_mail_detail.html",
    )

    def source(self, relative_path):
        return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    def test_user_controlled_json_uses_django_json_script(self):
        for relative_path in self.json_templates:
            with self.subTest(template=relative_path):
                source = self.source(relative_path)
                self.assertIn("|json_script:", source)
                self.assertNotIn("|safe", source)

    def test_secure_mail_has_no_executable_inline_script(self):
        source = self.source("templates/core/secure_mail_inbox.html")
        self.assertNotIn("<script>", source)
        self.assertNotIn("innerHTML", source)

    def test_json_bridge_loads_before_main_application(self):
        source = self.source("templates/base.html")
        bridge = source.index("core/json_data.js")
        application = source.index("core/app.js")
        self.assertLess(bridge, application)

    def test_json_bridge_uses_dom_text_not_html_parsing(self):
        source = self.source("core/static/core/json_data.js")
        self.assertNotIn("innerHTML", source)
        self.assertIn("textContent", source)
        self.assertIn("createElement", source)

    def test_mobile_navigation_keeps_four_primary_destinations(self):
        source = self.source("templates/base.html")
        self.assertNotIn('href="{% url \'chat\' %}"', source)
        self.assertIn("'private_chat' in request.resolver_match.url_name", source)


class MiddlewareSecurityRegressionTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    def middleware_for(self, response):
        return SecurityHeadersMiddleware(lambda _request: response)

    def test_csp_keeps_inline_scripts_disabled(self):
        response = self.middleware_for(HttpResponse("ok"))(self.request)
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("'unsafe-inline'", policy)

    def test_scheme_relative_redirect_is_rejected(self):
        response = HttpResponse(status=302)
        response.headers["Location"] = "//example.org/path"
        secured = self.middleware_for(response)(self.request)
        self.assertEqual(secured.headers["Location"], "/")

    def test_normal_local_redirect_is_preserved(self):
        response = HttpResponse(status=302)
        response.headers["Location"] = "/uebersicht/"
        secured = self.middleware_for(response)(self.request)
        self.assertEqual(secured.headers["Location"], "/uebersicht/")


class ConcurrencyGuardRegressionTests(SimpleTestCase):
    def test_task_board_locks_stable_rows_before_first_insert(self):
        source = (PROJECT_ROOT / "core/task_board.py").read_text(encoding="utf-8")
        self.assertIn("Station.objects.select_for_update()", source)
        self.assertIn("StationTask.objects.select_for_update()", source)
