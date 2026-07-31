from django.urls import path

from . import api


app_name = "api"

urlpatterns = [
    path("status/", api.status, name="status"),
    path("uebersicht/", api.overview, name="overview"),
]
