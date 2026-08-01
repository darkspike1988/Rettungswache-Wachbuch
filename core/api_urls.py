from django.urls import path

from . import api


app_name = "api"

urlpatterns = [
    path("anmeldung/", api.login, name="login"),
    path("status/", api.status, name="status"),
    path("uebersicht/", api.overview, name="overview"),
    path("uebergaben/", api.handovers, name="handover_list"),
    path("uebergaben/<int:pk>/", api.handover_detail, name="handover_detail"),
    path("uebergaben/<int:pk>/status/", api.handover_set_status, name="handover_status"),
    path("kalender/", api.calendar, name="calendar"),
    path("kaffeekasse/", api.coffee, name="coffee"),
    path("checklisten/", api.checklists, name="checklists"),
    path("checklisten/<int:pk>/erledigt/", api.checklist_complete, name="checklist_complete"),
]
