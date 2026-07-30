from django.urls import path
from django.views.generic import RedirectView

from . import views
from . import views_twofactor


urlpatterns = [
    path("zugang/", views.access, name="access"),
    path("impressum/", views.imprint, name="imprint"),
    path("datenschutz/", views.privacy, name="privacy"),
    path("barrierefreiheit/", views.accessibility, name="accessibility"),
    path("demo/", views.demo, name="demo"),
    path("demo/start/", views.demo_start, name="demo_start"),

    # Die Woche ist die Anwendung. Kein Dashboard davor.
    path("", views.handover_week, name="home"),
    path("woche/pdf/", views.handover_week_pdf, name="handover_week_pdf"),
    path("woche/<str:tag>/team/", views.daily_team_update, name="daily_team_update"),

    path("einrichtung/", views.setup_wizard, name="setup_wizard"),
    path("einrichtung/<str:step>/", views.setup_wizard, name="setup_wizard"),

    # Eine Liste mit Filtern und Suche dient dem Wiederfinden - also heisst sie so.
    path("suchen/", views.handover_list, name="handover_search"),
    path("eintrag/neu/", views.handover_create, name="handover_create"),
    path("eintrag/<int:pk>/", views.handover_detail, name="handover_detail"),
    path("eintrag/<int:pk>/bearbeiten/", views.handover_edit, name="handover_edit"),
    path("eintrag/<int:pk>/gelesen/", views.handover_acknowledge, name="handover_acknowledge"),
    path("eintrag/<int:pk>/status/", views.handover_status, name="handover_status"),

    # Abgehakt wird beim Tag, angelegt wird im Wachenbereich.
    path("aufgaben/<str:tag>/", views.tasks_day, name="tasks_day"),
    path("aufgaben/<str:tag>/<int:item_pk>/", views.task_mark, name="task_mark"),
    path("aufgaben/<str:tag>/<int:item_pk>/mangel/", views.task_defect, name="task_defect"),

    path("kalender/", views.calendar_view, name="calendar"),
    path("kalender/neu/", views.calendar_create, name="calendar_create"),
    path("geburtstage/", views.birthdays, name="birthdays"),
    path("geburtstage/einstellung/", views.birthday_settings, name="birthday_settings"),
    path("kaffeekasse/", views.coffee, name="coffee"),
    path("kaffeekasse/neu/", views.coffee_create, name="coffee_create"),
    path("kaffeekasse/<int:pk>/korrigieren/", views.coffee_correct, name="coffee_correct"),
    path("kaffeekasse/zahlungsangaben/", views.coffee_payment_update, name="coffee_payment_update"),
    path("lage/", views.feeds, name="feeds"),
    path("lage/muellabfuhr/", views.waste_source_update, name="waste_source_update"),

    # Organisatorisches der Wache an einem Ort.
    path("wache/", views.station_area, name="station_area"),
    path("wache/team/", views.team, name="team"),
    path("wache/team/freigeben/", views.team_create, name="team_create"),
    path("wache/team/<int:pk>/", views.membership_update, name="membership_update"),
    path("wache/aufgabenlisten/", views.task_lists, name="task_lists"),
    path("wache/aufgabenlisten/neu/", views.task_list_create, name="task_list_create"),
    path("wache/aufgabenlisten/<int:pk>/", views.task_list_edit, name="task_list_edit"),
    path("wache/aufgabenlisten/<int:pk>/aktiv/", views.task_list_toggle, name="task_list_toggle"),
    path("wache/aufgabenlisten/<int:pk>/aufgabe/", views.task_item_create, name="task_item_create"),
    path(
        "wache/aufgabenlisten/<int:pk>/aufgabe/<int:item_pk>/",
        views.task_item_action, name="task_item_action",
    ),
    path("wache/einstellungen/", views.station_settings, name="station_settings"),
    path("wache/einstellungen/adresse/", views.station_geocode, name="station_geocode"),
    path("wache/wechseln/", views.switch_station, name="switch_station"),
    path("wache/audit/", views.audit_log, name="audit_log"),

    # Persoenliches liegt beim eigenen Namen, nicht in einer Sammelschublade.
    path("konto/", views.account, name="account"),
    path("konto/zwei-faktor/", views_twofactor.twofactor_status, name="twofactor_status"),
    path("konto/zwei-faktor/einrichten/", views_twofactor.twofactor_setup, name="twofactor_setup"),
    path("konto/zwei-faktor/codes/", views_twofactor.twofactor_codes, name="twofactor_codes"),
    path("konto/zwei-faktor/codes/neu/", views_twofactor.twofactor_regenerate, name="twofactor_regenerate"),
    path("konto/zwei-faktor/deaktivieren/", views_twofactor.twofactor_disable, name="twofactor_disable"),

    # Alte Adressen bleiben erreichbar, damit Lesezeichen nicht ins Leere laufen.
    path("wochenprotokoll/", RedirectView.as_view(pattern_name="home", permanent=True)),
    path("uebergaben/", RedirectView.as_view(pattern_name="handover_search", permanent=True)),
    path("mehr/", RedirectView.as_view(pattern_name="station_area", permanent=True)),
]
