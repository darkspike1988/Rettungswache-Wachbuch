from django.contrib import admin

from .models import (
    AuditEvent,
    BirthdayPreference,
    CalendarEvent,
    CoffeeEntry,
    FeedItem,
    FeedSource,
    HandoverEntry,
    HandoverRevision,
    Membership,
    Station,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "calendar_enabled",
        "birthdays_enabled",
        "coffee_enabled",
        "feeds_enabled",
    )
    list_filter = ("is_active",)

    def get_readonly_fields(self, request, obj=None):
        return ("slug",) if obj else ()


@admin.register(Membership)
class MembershipAdmin(ReadOnlyAdmin):
    list_display = ("user", "station", "role", "is_active")
    list_filter = ("station", "role", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(HandoverEntry)
class HandoverAdmin(ReadOnlyAdmin):
    list_display = ("title", "station", "category", "priority", "status", "updated_at")
    list_filter = ("station", "category", "priority", "status")


@admin.register(HandoverRevision)
class HandoverRevisionAdmin(ReadOnlyAdmin):
    list_display = ("handover", "version", "changed_by", "created_at")


@admin.register(CalendarEvent)
class CalendarEventAdmin(ReadOnlyAdmin):
    list_display = ("title", "station", "starts_at", "ends_at", "created_by")
    list_filter = ("station",)


@admin.register(BirthdayPreference)
class BirthdayPreferenceAdmin(ReadOnlyAdmin):
    list_display = ("user", "station", "is_visible", "updated_at")
    list_filter = ("station", "is_visible")


@admin.register(CoffeeEntry)
class CoffeeEntryAdmin(ReadOnlyAdmin):
    list_display = ("member", "amount_cents", "reason", "created_by", "created_at")
    list_filter = ("station",)


@admin.register(FeedSource)
class FeedSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "locality", "is_enabled", "last_success_at")
    list_filter = ("kind", "is_enabled")
    readonly_fields = ("last_success_at", "last_error_at", "last_error")


@admin.register(FeedItem)
class FeedItemAdmin(ReadOnlyAdmin):
    list_display = ("title", "source", "published_at", "imported_at")
    list_filter = ("source",)


@admin.register(AuditEvent)
class AuditEventAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "actor", "station", "action", "object_type", "object_id")
    list_filter = ("station", "action", "object_type")


admin.site.site_header = "Wachbuch-Verwaltung"
admin.site.site_title = "Wachbuch"
