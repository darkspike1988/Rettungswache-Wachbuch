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


def application_metadata(request):
    return {
        "app_name": settings.APP_NAME,
        "source_url": settings.SOURCE_URL,
        "trust_tailscale_headers": settings.TRUST_TAILSCALE_HEADERS,
    }


def operator_metadata(request):
    return {
        "operator_name": settings.OPERATOR_NAME,
        "operator_address": settings.OPERATOR_ADDRESS,
        "operator_representative": settings.OPERATOR_REPRESENTATIVE,
        "operator_contact": settings.OPERATOR_CONTACT,
        "dpo_contact": settings.DPO_CONTACT,
        "accessibility_contact": settings.ACCESSIBILITY_CONTACT,
    }
