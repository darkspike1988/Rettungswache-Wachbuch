from django.urls import path

from . import views, wachalltag

urlpatterns = [
    path("", wachalltag.api_root, name="api_v1_root"),
    path("openapi.yaml", views.openapi_spec, name="api_v1_openapi"),
    # English / Paperless-style
    path("token/", views.obtain_token, name="api_v1_token"),
    path("me/", wachalltag.me, name="api_v1_me"),
    path("handovers/", views.handovers_list, name="api_v1_handovers"),
    path("handovers/<int:pk>/", views.handover_detail, name="api_v1_handover_detail"),
    path("handovers/<int:pk>/status/", views.handover_set_status, name="api_v1_handover_status"),
    path("handovers/<int:pk>/acks/", wachalltag.handover_acks, name="api_v1_handover_acks"),
    path("handovers/<int:pk>/ack/", wachalltag.handover_ack, name="api_v1_handover_ack"),
    path("defects/", wachalltag.defects_list, name="api_v1_defects"),
    path("defects/<int:pk>/", wachalltag.defect_detail, name="api_v1_defect_detail"),
    path("defects/<int:pk>/status/", wachalltag.defect_status, name="api_v1_defect_status"),
    path("defects/<int:pk>/attachments/", wachalltag.defect_attachments, name="api_v1_defect_attachments"),
    path("attachments/<int:pk>/", wachalltag.attachment_download, name="api_v1_attachment_download"),
    path("assets/", wachalltag.assets_list, name="api_v1_assets"),
    path("assets/<slug:asset_id>/status/", wachalltag.asset_status, name="api_v1_asset_status"),
    path("inventory/", wachalltag.inventory_list, name="api_v1_inventory"),
    path("inventory/<slug:item_id>/checkout/", wachalltag.inventory_checkout, name="api_v1_inventory_checkout"),
    path("inventory/<slug:item_id>/checkin/", wachalltag.inventory_checkin, name="api_v1_inventory_checkin"),
    path("reports/", wachalltag.reports, name="api_v1_reports"),
    # German aliases (unified with PR #12 / Wachbuch-Client)
    path("anmeldung/", views.obtain_token, name="api_v1_anmeldung"),
    path("status/", views.api_status, name="api_v1_status"),
    path("uebersicht/", wachalltag.overview, name="api_v1_overview"),
    path("uebergaben/", views.handovers_list, name="api_v1_uebergaben"),
    path("uebergaben/<int:pk>/", views.handover_detail, name="api_v1_uebergabe_detail"),
    path("uebergaben/<int:pk>/status/", views.handover_set_status, name="api_v1_uebergabe_status"),
    path("kalender/", views.calendar_api, name="api_v1_kalender"),
    path("kaffeekasse/", views.coffee_api, name="api_v1_kaffeekasse"),
    path("checklisten/", wachalltag.checklists_api, name="api_v1_checklisten"),
    path("checklisten/<int:pk>/erledigt/", wachalltag.checklist_complete_api, name="api_v1_checkliste_erledigt"),
    path("checklisten/<int:pk>/abschluss/", wachalltag.checklist_complete_api, name="api_v1_checkliste_abschluss"),
    path("checklisten/<int:pk>/schedule/", wachalltag.checklist_schedule, name="api_v1_checkliste_schedule"),
    path("pinnwand/", views.pinboard_api, name="api_v1_pinnwand"),
]
