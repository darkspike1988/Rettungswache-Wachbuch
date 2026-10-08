"""Vertragstest zwischen implementierter API und OpenAPI-Spezifikation.

Ursache: `core/api/openapi_v1.yaml` stand auf 1.2.2 und dokumentierte 14 real
vorhandene Endpunkte nicht, die der offizielle Client bereits aufruft
(`/chat/*`, `/post/*`, `/pinnwand/` und die deutschen Handovers-Aliase
`/uebergaben/*`). Der veröffentlichte Vertrag hinkte damit der Implementierung
nach, und eine Client-Gegenprüfung war nicht möglich.

Dieser Test prüft beide Richtungen und zusätzlich das tatsächliche Verhalten:

1. Jeder dokumentierte Pfad existiert als Django-Route.
2. Jede Django-Route ist dokumentiert.
3. Jede dokumentierte Methode wird von der Route akzeptiert (kein HTTP 405).

Der Test liest die YAML-Datei bewusst ohne YAML-Abhängigkeit: Das Projekt hat
kein PyYAML als Laufzeitabhängigkeit, und ein Vertragstest darf keine neue
Abhängigkeit nur für sich selbst erzwingen. Geprüft wird das `paths:`-Block
dieser Datei, nicht beliebiges YAML.
"""

import re
from pathlib import Path

from django.test import TestCase

SPEC_PATH = Path(__file__).resolve().parent / "api" / "openapi_v1.yaml"
API_PREFIX = "/api/v1"
METHODS = ("get", "post", "put", "patch", "delete")

_SPEC_PARAM = re.compile(r"\{[^}]+\}")
_DJANGO_PARAM = re.compile(r"\(\?P<[^>]+>[^)]*\)")
# `str(RoutePattern)` keeps the converter syntax used in urls.py, so both
# `<int:pk>` and `<slug:item_id>` have to be reduced as well.
_DJANGO_ROUTE_PARAM = re.compile(r"<[^>]+>")


def normalise_path(path):
    """Reduce a spec path or a Django route to a comparable shape.

    `/chat/groups/{id}/`, `chat/groups/(?P<pk>[0-9]+)/` and
    `chat/groups/<int:pk>/` all become `/chat/groups/{}/`. Parameter names are
    intentionally not compared: the contract guarantees a parameter, not its
    client-side name.
    """
    path = _SPEC_PARAM.sub("{}", path)
    path = _DJANGO_PARAM.sub("{}", path)
    path = _DJANGO_ROUTE_PARAM.sub("{}", path)
    path = path.replace("^", "").replace("$", "")
    if not path.startswith("/"):
        path = "/" + path
    return path


def parse_spec(text):
    """Return {normalised path: {methods}} for the `paths:` block of the spec."""
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.rstrip() == "paths:"),
        None,
    )
    if start is None:
        raise AssertionError("openapi_v1.yaml enthält keinen paths:-Block")

    paths = {}
    current = None
    for line in lines[start + 1:]:
        if line.startswith("components:"):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 2 and stripped.endswith(":") and stripped.startswith("/"):
            current = normalise_path(stripped[:-1])
            paths[current] = set()
        elif indent == 4 and current is not None and stripped.endswith(":"):
            method = stripped[:-1]
            if method in METHODS:
                paths[current].add(method)
    return paths


def implemented_routes():
    """Return {normalised path: route name} for core/api/urls.py."""
    from core.api import urls as api_urls

    routes = {}
    for pattern in api_urls.urlpatterns:
        routes[normalise_path(str(pattern.pattern))] = getattr(pattern, "name", None)
    return routes


def concrete_url(normalised_path):
    """Build a callable URL, substituting every parameter placeholder."""
    return API_PREFIX + re.sub(r"\{\}", "1", normalised_path)


class SpecParserTests(TestCase):
    """The parser itself must catch drift, otherwise the guard is worthless."""

    def test_parser_reads_paths_and_methods(self):
        spec = parse_spec(
            "paths:\n"
            "  /alpha/:\n"
            "    get:\n"
            "      summary: x\n"
            "    post:\n"
            "      summary: y\n"
            "  /alpha/{id}/:\n"
            "    delete:\n"
            "      summary: z\n"
            "components:\n"
            "  schemas: {}\n"
        )
        self.assertEqual(
            spec,
            {"/alpha/": {"get", "post"}, "/alpha/{}/": {"delete"}},
        )

    def test_parser_ignores_a_second_document_root_key(self):
        spec = parse_spec("paths:\n  /a/:\n    get:\n      summary: x\ncomponents:\n")
        self.assertEqual(set(spec), {"/a/"})

    def test_parser_rejects_a_spec_without_paths_block(self):
        with self.assertRaises(AssertionError):
            parse_spec("openapi: 3.0.3\n")

    def test_normalise_path_matches_django_and_spec_parameters(self):
        self.assertEqual(
            normalise_path("chat/groups/(?P<pk>[0-9]+)/"),
            normalise_path("/chat/groups/{id}/"),
        )
        self.assertEqual(
            normalise_path("assets/(?P<asset_id>[-a-zA-Z0-9_]+)/status/"),
            normalise_path("/assets/{asset_id}/status/"),
        )
        # `str(RoutePattern)` keeps the converter syntax from urls.py.
        self.assertEqual(
            normalise_path("chat/groups/<int:pk>/members/"),
            normalise_path("/chat/groups/{id}/members/"),
        )
        self.assertEqual(
            normalise_path("inventory/<slug:item_id>/checkin/"),
            normalise_path("/inventory/{item_id}/checkin/"),
        )


class ApiContractTests(TestCase):
    """Both directions of the published contract."""

    @classmethod
    def setUpTestData(cls):
        cls.spec = parse_spec(SPEC_PATH.read_text(encoding="utf-8"))
        cls.routes = implemented_routes()

    def test_spec_declares_a_version(self):
        text = SPEC_PATH.read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^  version: "\d+\.\d+\.\d+"$')

    def test_every_documented_path_is_implemented(self):
        missing = sorted(set(self.spec) - set(self.routes))
        self.assertEqual(
            missing,
            [],
            "In openapi_v1.yaml dokumentiert, aber nicht in core/api/urls.py "
            f"implementiert: {missing}",
        )

    def test_every_implemented_path_is_documented(self):
        undocumented = sorted(set(self.routes) - set(self.spec))
        self.assertEqual(
            undocumented,
            [],
            "In core/api/urls.py implementiert, aber nicht in "
            f"openapi_v1.yaml dokumentiert: {undocumented}",
        )

    def test_every_route_documents_at_least_one_method(self):
        empty = sorted(path for path, methods in self.spec.items() if not methods)
        self.assertEqual(empty, [], f"Pfad ohne dokumentierte Methode: {empty}")

    def test_spec_is_served_over_the_api(self):
        """The file is only a contract if the running server actually ships it."""
        response = self.client.get(f"{API_PREFIX}/openapi.yaml")
        self.assertEqual(response.status_code, 200)
        served = response.content.decode("utf-8")
        self.assertIn('version: "1.3.0"', served)
        self.assertEqual(parse_spec(served), self.spec)

    def test_documented_methods_are_accepted(self):
        """A wrong method must yield 405; anything else means the method exists."""
        rejected = {}
        for path, methods in sorted(self.spec.items()):
            url = concrete_url(path)
            for method in sorted(methods):
                response = self.client.generic(
                    method.upper(),
                    url,
                    data="{}",
                    content_type="application/json",
                )
                if response.status_code == 405:
                    rejected.setdefault(path, []).append(method)
        self.assertEqual(
            rejected,
            {},
            "Dokumentierte Methoden, die die Route ablehnt: "
            f"{ {path: sorted(ms) for path, ms in rejected.items()} }",
        )
