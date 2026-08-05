from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .access import CONTENT_ROLES, membership_required
from .models import DismissedNotice

INSTALL_NOTICE_KEY = "install-app:v1"


@membership_required(CONTENT_ROLES)
@require_POST
def dismiss_install_notice(request):
    DismissedNotice.objects.get_or_create(
        user=request.user,
        notice_key=INSTALL_NOTICE_KEY,
    )
    return JsonResponse({"ok": True})
