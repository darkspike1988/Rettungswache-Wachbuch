from django.conf import settings

from .access import available_memberships, get_membership


def current_membership(request):
    if not request.user.is_authenticated:
        return {"current_membership": None, "other_memberships": []}
    membership = get_membership(request.user, request.session)
    others = [
        item for item in available_memberships(request.user)
        if membership is None or item.pk != membership.pk
    ]
    return {"current_membership": membership, "other_memberships": others}


# Seiten, die zum Wachenbereich gehoeren. Nur damit die Navigation weiss, wo
# sie sich befindet - keine Rechtepruefung.
STATION_AREA_PAGES = frozenset({
    "station_area", "station_settings", "station_geocode", "switch_station",
    "team", "team_create", "membership_update", "audit_log",
    "birthdays", "birthday_settings",
    "coffee", "coffee_create", "coffee_correct", "coffee_payment_update",
    "feeds", "waste_source_update",
    "calendar", "calendar_create",
    "task_lists", "task_list_create", "task_list_edit", "task_list_toggle",
    "task_item_create", "task_item_action",
})

# Seiten, die an einem Tag der Woche haengen. Wer Aufgaben abhakt, ist in der
# Woche unterwegs - nicht in einem eigenen Menuepunkt.
WEEK_AREA_PAGES = frozenset({
    "home", "daily_team_update", "tasks_day", "task_mark", "task_defect",
})


def navigation(request):
    return {
        "station_area_pages": STATION_AREA_PAGES,
        "week_area_pages": WEEK_AREA_PAGES,
    }


def application_metadata(request):
    return {
        "app_name": settings.APP_NAME,
        "source_url": settings.SOURCE_URL,
        "trust_tailscale_headers": settings.TRUST_TAILSCALE_HEADERS,
    }


def demo_session(request):
    return {"is_demo_session": bool(request.session.get("is_demo_session"))}


def operator_metadata(request):
    return {
        "operator_name": settings.OPERATOR_NAME,
        "operator_address": settings.OPERATOR_ADDRESS,
        "operator_representative": settings.OPERATOR_REPRESENTATIVE,
        "operator_contact": settings.OPERATOR_CONTACT,
        "dpo_contact": settings.DPO_CONTACT,
        "accessibility_contact": settings.ACCESSIBILITY_CONTACT,
    }
