from django.urls import path

from . import views

urlpatterns = [
    path("", views.api_root, name="api_v1_root"),
    path("openapi.yaml", views.openapi_spec, name="api_v1_openapi"),
    # English / Paperless-style
    path("token/", views.obtain_token, name="api_v1_token"),
    path("me/", views.me, name="api_v1_me"),
    path("handovers/", views.handovers_list, name="api_v1_handovers"),
    path("handovers/<int:pk>/", views.handover_detail, name="api_v1_handover_detail"),
    path("handovers/<int:pk>/status/", views.handover_set_status, name="api_v1_handover_status"),
    # German aliases (unified with PR #12 / Wachbuch-Client)
    path("anmeldung/", views.obtain_token, name="api_v1_anmeldung"),
    path("status/", views.api_status, name="api_v1_status"),
    path("uebersicht/", views.overview, name="api_v1_overview"),
    path("uebergaben/", views.handovers_list, name="api_v1_uebergaben"),
    path("uebergaben/<int:pk>/", views.handover_detail, name="api_v1_uebergabe_detail"),
    path("uebergaben/<int:pk>/status/", views.handover_set_status, name="api_v1_uebergabe_status"),
    path("kalender/", views.calendar_api, name="api_v1_kalender"),
    path("kaffeekasse/", views.coffee_api, name="api_v1_kaffeekasse"),
    path("checklisten/", views.checklists_api, name="api_v1_checklisten"),
    path("checklisten/<int:pk>/erledigt/", views.checklist_complete_api, name="api_v1_checkliste_erledigt"),
]
