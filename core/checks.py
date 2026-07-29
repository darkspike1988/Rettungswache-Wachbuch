from django.conf import settings
from django.core.checks import Warning, register


REQUIRED_OPERATOR_SETTINGS = [
    ("OPERATOR_NAME", "Name der verantwortlichen Stelle (Impressum, Datenschutz)"),
    ("OPERATOR_ADDRESS", "Anschrift der verantwortlichen Stelle (Impressum)"),
    ("OPERATOR_CONTACT", "Kontaktweg der verantwortlichen Stelle (Impressum)"),
    ("DPO_CONTACT", "Kontakt der/des Datenschutzbeauftragten (Datenschutzerklaerung)"),
    ("ACCESSIBILITY_CONTACT", "Kontakt fuer Barrierefreiheits-Feedback"),
]


@register("wachbuch")
def check_demo_mode(app_configs, **kwargs):
    """Im Demobetrieb bekommt jeder Besucher eine Sitzung. Das ist gewollt,
    darf aber nie unbemerkt auf einer echten Wache laufen."""
    if not settings.DEMO_MODE:
        return []
    return [
        Warning(
            "DEMO_MODE ist aktiv: jeder Besucher kann eine Sitzung als Demokonto "
            "starten.",
            hint=(
                "Auf einer Instanz mit echten Wachendaten muss DEMO_MODE=false "
                "gesetzt sein."
            ),
            id="wachbuch.W002",
        )
    ]


@register("wachbuch")
def check_operator_settings(app_configs, **kwargs):
    """Ohne diese Angaben zeigen Impressum, Datenschutz- und
    Barrierefreiheitserklaerung nur Platzhalter. Sobald die Anwendung
    oeffentlich erreichbar ist, ist das eine rechtliche Luecke."""
    if settings.DEBUG:
        return []
    missing = [
        f"{name} ({purpose})"
        for name, purpose in REQUIRED_OPERATOR_SETTINGS
        if not getattr(settings, name, "")
    ]
    if not missing:
        return []
    return [
        Warning(
            "Angaben zur verantwortlichen Stelle fehlen; die Rechtstexte zeigen "
            "Platzhalter statt echter Angaben.",
            hint=(
                "In .env setzen: " + ", ".join(missing) + ". "
                "Details in docs/COMPLIANCE-NRW.md."
            ),
            id="wachbuch.W001",
        )
    ]
