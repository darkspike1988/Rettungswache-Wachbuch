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


API_DOC = Path(__file__).resolve().parent.parent / "docs" / "API.md"
_ROW = re.compile(r"^\|\s*([A-Z/]+)\s*\|(.+?)\|\s*[^|]*\|\s*$")
_PATH_TOKEN = re.compile(r"`([^`]+)`")


def parse_api_doc_table(text):
    """Extract {normalised path: {methods}} from the endpoint table in API.md.

    The table groups several paths in one row, so the claimed method set applies
    to every path listed in that row. Rows whose first cell is not a method list
    (header, separator) are skipped.
    """
    claims = {}
    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        methods = {part.strip().lower() for part in match.group(1).split("/") if part.strip()}
        if not methods or not methods <= set(METHODS):
            continue
        for token in _PATH_TOKEN.findall(match.group(2)):
            token = token.strip()
            if not token.startswith("/"):
                continue
            if token.startswith(API_PREFIX):
                token = token[len(API_PREFIX):]
            claims.setdefault(normalise_path(token), set()).update(methods)
    return claims


def concrete_url(normalised_path):
    """Build a callable URL, substituting every parameter placeholder."""
    return API_PREFIX + re.sub(r"\{\}", "1", normalised_path)


def parse_schema(text, name):
    """Return {'required': [...], 'properties': {...}} for one schema block.

    Hand-rolled for the same reason as parse_spec: the project has no YAML
    dependency. Assumes the formatting used in openapi_v1.yaml - schema header
    at indent 4, `properties:` at indent 6, property keys at indent 8.
    """
    lines = text.splitlines()
    header = f"    {name}:"
    start = next((index for index, line in enumerate(lines) if line.rstrip() == header), None)
    if start is None:
        raise AssertionError(f"Schema {name} fehlt in openapi_v1.yaml")
    required = []
    properties = set()
    in_properties = False
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= 4:
            break
        if indent == 6 and stripped == "properties:":
            in_properties = True
            continue
        if indent == 6 and stripped.startswith("required:"):
            raw = stripped[len("required:"):].strip().strip("[]")
            required = [part.strip() for part in raw.split(",") if part.strip()]
            continue
        if not in_properties:
            continue
        if indent == 6:
            in_properties = False
            continue
        if indent == 8 and not stripped.startswith("-"):
            key = stripped.split(":", 1)[0].strip()
            if key:
                properties.add(key)
    return {"required": required, "properties": properties}


def served_version(text):
    """Read info.version from the spec text without a YAML parser."""
    match = re.search(r'(?m)^  version:\s*"?([0-9][^"\s]*)"?\s*$', text)
    if not match:
        raise AssertionError("openapi_v1.yaml enthält keine version unter info")
    return match.group(1)


def path_block(text, spec_path):
    """Return the raw YAML block of one path entry from openapi_v1.yaml."""
    lines = text.splitlines()
    header = f"  {spec_path}:"
    start = next((index for index, line in enumerate(lines) if line.rstrip() == header), None)
    if start is None:
        raise AssertionError(f"Pfad {spec_path} fehlt in openapi_v1.yaml")
    block = []
    for line in lines[start + 1:]:
        if line.strip() and (len(line) - len(line.lstrip())) <= 2:
            break
        block.append(line)
    return "\n".join(block)


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
        cls.spec_text = SPEC_PATH.read_text(encoding="utf-8")
        cls.spec = parse_spec(cls.spec_text)
        cls.routes = implemented_routes()

    def test_spec_declares_a_version(self):
        self.assertRegex(self.spec_text, r'(?m)^  version: "\d+\.\d+\.\d+"$')

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
        self.assertIn(served_version(self.spec_text), served)
        self.assertEqual(parse_spec(served), self.spec)

    def test_api_doc_table_names_only_documented_methods(self):
        """docs/API.md must not promise a method the specification does not document.

        The narrative table is what a client author reads first. A row like
        `GET/POST | /post/, /post/<id>/` claims POST on a GET-only route and
        sends the reader into a 405. The table may list a subset of the
        documented methods, never more.
        """
        claims = parse_api_doc_table(API_DOC.read_text(encoding="utf-8"))
        self.assertTrue(claims, "Keine Endpunktzeilen in docs/API.md gefunden")
        overclaimed = {}
        for path, methods in sorted(claims.items()):
            documented = self.spec.get(path)
            if documented is None:
                overclaimed[path] = sorted(methods)
                continue
            extra = methods - documented
            if extra:
                overclaimed[path] = sorted(extra)
        self.assertEqual(
            overclaimed,
            {},
            "docs/API.md nennt Pfade oder Methoden, die openapi_v1.yaml nicht "
            f"dokumentiert: {overclaimed}",
        )

    def test_defect_write_requires_title(self):
        """The creation schema must name the field the server rejects on.

        POST /defects/ answers 422 without a title. A schema that lists title
        only as an optional property tells a client author the opposite.
        """
        schema = parse_schema(self.spec_text, "DefectWrite")
        self.assertIn("title", schema["required"])

    def test_defect_patch_schema_matches_the_fields_the_handler_applies(self):
        """PATCH must not offer fields the handler silently ignores.

        defect_detail() applies exactly description, asset_ref, priority, owner
        and due_at. title and category are fixed at creation. Documenting the
        creation schema for PATCH promised editable fields that never change.
        """
        schema = parse_schema(self.spec_text, "DefectPatch")
        self.assertEqual(
            schema["properties"],
            {"description", "asset_ref", "priority", "owner", "due_at"},
        )
        self.assertNotIn("title", schema["properties"])

    def test_defect_patch_operation_uses_the_patch_schema(self):
        """The PATCH operation must reference DefectPatch, not DefectWrite."""
        _, separator, patch = path_block(self.spec_text, "/defects/{id}/").partition("    patch:")
        self.assertTrue(separator, "PATCH-Operation fehlt unter /defects/{id}/")
        self.assertIn("#/components/schemas/DefectPatch", patch.split("responses:", 1)[0])

    def test_documented_methods_match_accepted_methods(self):
        """Documented methods and actually accepted methods must be identical.

        A wrong method yields HTTP 405, so probing every documented path with
        every method yields the real, server-enforced method set. Comparing it
        in both directions catches a method that is documented but not served
        *and* a served method that nobody documented.
        """
        documented_missing = {}
        undocumented_served = {}
        for path, documented in sorted(self.spec.items()):
            url = concrete_url(path)
            served = set()
            for method in METHODS:
                response = self.client.generic(
                    method.upper(),
                    url,
                    data="{}",
                    content_type="application/json",
                )
                if response.status_code != 405:
                    served.add(method)
            if not documented <= served and documented:
                documented_missing[path] = sorted(documented - served)
            if served - documented:
                undocumented_served[path] = sorted(served - documented)
        self.assertEqual(
            documented_missing,
            {},
            "Dokumentierte, aber vom Server abgelehnte Methoden: "
            f"{documented_missing}",
        )
        self.assertEqual(
            undocumented_served,
            {},
            "Vom Server akzeptierte, aber nicht dokumentierte Methoden: "
            f"{undocumented_served}",
        )

    def test_handover_ack_operation_requires_version(self):
        """ack-Operation verlangt requestBody.required=true und required:[version] mit integer minimum 1."""
        _, separator, post = path_block(self.spec_text, "/handovers/{id}/ack/").partition("    post:")
        self.assertTrue(separator, "POST-Operation fehlt")

        request_body = post.split("responses:", 1)[0]
        self.assertIn("required: true", request_body)
        self.assertIn("required: [version]", request_body)
        self.assertIn("type: integer", request_body)
        self.assertIn("minimum: 1", request_body)

        # HandoverAck Schema Output:
        text_lines = self.spec_text.splitlines()
        ack_idx = next(i for i, line in enumerate(text_lines) if line.startswith("    HandoverAck:"))
        version_line = next(line for line in text_lines[ack_idx:ack_idx+10] if "version:" in line)
        self.assertIn("nullable: true", version_line)

        # Stale-Revision -> 409 muss am Endpunkt dokumentiert sein.
        block = path_block(self.spec_text, "/handovers/{id}/ack/")
        self.assertIn('"409"', block)

    def test_error_code_enum_covers_conflict(self):
        """Der Server liefert bei stale Revision code=conflict; der Vertrag muss ihn nennen."""
        _, separator, block = self.spec_text.partition("    ErrorResponse:")
        self.assertTrue(separator, "ErrorResponse-Schema fehlt in openapi_v1.yaml")
        enum_line = next(
            line for line in block.splitlines()
            if "enum:" in line and "validation_error" in line
        )
        self.assertIn("conflict", enum_line)

        doc_line = next(
            line for line in API_DOC.read_text(encoding="utf-8").splitlines()
            if line.startswith("Kanonische Codes:")
        )
        self.assertIn("`conflict`", doc_line)
