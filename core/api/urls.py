from django.urls import path

from . import views

urlpatterns = [
    path("", views.api_root, name="api_v1_root"),
    path("openapi.yaml", views.openapi_spec, name="api_v1_openapi"),
    path("token/", views.obtain_token, name="api_v1_token"),
    path("me/", views.me, name="api_v1_me"),
    path("handovers/", views.handovers_list, name="api_v1_handovers"),
]
