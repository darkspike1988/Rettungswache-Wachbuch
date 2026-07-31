from django.urls import path

from . import api


app_name = "api"

urlpatterns = [
    path("anmeldung/", api.login, name="login"),
    path("status/", api.status, name="status"),
    path("uebersicht/", api.overview, name="overview"),
    path("uebergaben/", api.handover_list, name="handover_list"),
    path("uebergaben/<int:pk>/", api.handover_detail, name="handover_detail"),
    path("kalender/", api.calendar, name="calendar"),
    path("kaffeekasse/", api.coffee, name="coffee"),
]
