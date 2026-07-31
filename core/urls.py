from django.urls import path

from . import views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("zugang/", views.access, name="access"),
    path("uebersicht/", views.dashboard, name="dashboard"),
    path("uebergaben/", views.handover_list, name="handover_list"),
    path("uebergaben/neu/", views.handover_create, name="handover_create"),
    path("uebergaben/<int:pk>/", views.handover_detail, name="handover_detail"),
    path("uebergaben/<int:pk>/status/", views.handover_status, name="handover_status"),
    path("kalender/", views.calendar_view, name="calendar"),
    path("kalender/neu/", views.calendar_create, name="calendar_create"),
    path("kalender/<int:pk>/termin.ics", views.calendar_event_ics, name="calendar_event_ics"),
    path("geburtstage/", views.birthdays, name="birthdays"),
    path("geburtstage/einstellung/", views.birthday_settings, name="birthday_settings"),
    path("kaffeekasse/", views.coffee, name="coffee"),
    path("kaffeekasse/neu/", views.coffee_create, name="coffee_create"),
    path("kaffeekasse/<int:pk>/korrigieren/", views.coffee_correct, name="coffee_correct"),
    path("lage/", views.feeds, name="feeds"),
    path("aufgaben/", views.tasks_today, name="tasks_today"),
    path("aufgaben/woche/", views.tasks_week, name="tasks_week"),
    path("aufgaben/verwaltung/", views.tasks_manage, name="tasks_manage"),
    path("aufgaben/neu/", views.task_create, name="task_create"),
    path("aufgaben/<int:pk>/bearbeiten/", views.task_edit, name="task_edit"),
    path("aufgaben/<int:pk>/status/", views.task_toggle, name="task_toggle"),
    path("mehr/", views.more, name="more"),
    path("team/", views.team, name="team"),
    path("team/freigeben/", views.team_create, name="team_create"),
    path("team/<int:pk>/", views.membership_update, name="membership_update"),
    path("einstellungen/", views.station_settings, name="station_settings"),
    path("audit/", views.audit_log, name="audit_log"),
]
