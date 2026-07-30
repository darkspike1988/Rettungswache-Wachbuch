from django.conf import settings

from .access import get_membership


def current_membership(request):
    membership = get_membership(request.user) if request.user.is_authenticated else None
    return {"current_membership": membership}


def application_metadata(request):
    return {
        "app_name": settings.APP_NAME,
        "source_url": settings.SOURCE_URL,
    }
