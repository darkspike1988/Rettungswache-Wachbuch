from django.conf import settings

from .access import CONTENT_ROLES, get_membership
from .models import HandoverEntry


def current_membership(request):
    membership = get_membership(request.user) if request.user.is_authenticated else None
    nav_urgent_count = 0
    if membership and membership.role in CONTENT_ROLES:
        nav_urgent_count = (
            HandoverEntry.objects.filter(
                station=membership.station,
                priority=HandoverEntry.Priority.URGENT,
            )
            .exclude(status=HandoverEntry.Status.DONE)
            .count()
        )
    return {
        "current_membership": membership,
        "nav_urgent_count": nav_urgent_count,
    }


def application_metadata(request):
    return {
        "app_name": settings.APP_NAME,
        "source_url": settings.SOURCE_URL,
        "app_version": settings.APP_VERSION,
    }
