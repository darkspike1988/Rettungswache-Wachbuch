"""Audit logging service for Rettungswache-Wachbuch.

This module provides automatic audit logging for all model changes using Django signals.
It captures:
- Who made the change (actor)
- What was changed (action, object type, object ID)
- When it happened (timestamp)
- Additional context (IP address, user agent, metadata)

Usage:
    Import this module to enable audit logging:
    from core import audit  # noqa: F401
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import AuditEvent

logger = logging.getLogger(__name__)

# Models to exclude from audit logging
EXCLUDED_MODELS = {
    "AuditEvent",
    "RateLimit",
    "Session",
    "ContentType",
    "Permission",
    "Group",
}

# Actions that should not be logged
EXCLUDED_ACTIONS = {
    "autocreated",
    "auto_now",
    "auto_now_add",
}


def get_client_ip(request) -> str | None:
    """Extract client IP address from request."""
    if request is None:
        return None
    
    trusted = bool(getattr(settings, "TRUSTED_PROXY", False))
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    
    if trusted and forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = (request.META.get("REMOTE_ADDR") or "").strip()
    
    if not ip or len(ip) > 64:
        return None
    return ip


def get_user_agent(request) -> str:
    """Extract user agent from request."""
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:500]


def get_current_user() -> User | None:
    """Get the current user from thread-local storage."""
    from django.contrib.auth import get_user
    from django.contrib.auth.models import AnonymousUser
    
    user = get_user(getattr(settings, "_current_request", None))
    if isinstance(user, AnonymousUser):
        return None
    return user


def get_current_request():
    """Get the current request from thread-local storage."""
    return getattr(settings, "_current_request", None)


def get_station_from_user(user: User | None) -> Any:
    """Get the station for a user (simplified for now)."""
    if user is None:
        return None
    
    # Import here to avoid circular imports
    from .models import Membership
    
    # Get active membership
    membership = Membership.objects.filter(
        user=user, is_active=True
    ).select_related("station").first()
    
    if membership:
        return membership.station
    return None


def create_audit_event(
    action: str,
    object_type: str,
    object_id: str | None = None,
    object_repr: str = "",
    actor: User | None = None,
    station: Any = None,
    metadata: dict[str, Any] | None = None,
    request = None,
) -> AuditEvent | None:
    """Create an audit event record."""
    try:
        # Skip if action is excluded
        if action in EXCLUDED_ACTIONS:
            return None
        
        # Get IP and user agent from request
        ip_address = get_client_ip(request) if request else None
        user_agent = get_user_agent(request) if request else ""
        
        # Create audit event
        event = AuditEvent(
            action=action,
            object_type=object_type,
            object_id=str(object_id) if object_id else "",
            object_repr=str(object_repr)[:200],
            actor=actor,
            station=station,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        event.save()
        return event
    except Exception as e:
        logger.error(f"Failed to create audit event: {e}")
        return None


def get_object_repr(obj) -> str:
    """Get a string representation of an object."""
    if obj is None:
        return ""
    
    # Try __str__ first
    if hasattr(obj, "__str__"):
        try:
            return str(obj)[:200]
        except Exception:
            pass
    
    # Try __repr__
    if hasattr(obj, "__repr__"):
        try:
            return repr(obj)[:200]
        except Exception:
            pass
    
    # Fallback to class name + ID
    if hasattr(obj, "pk"):
        return f"{obj.__class__.__name__}(id={obj.pk})"
    
    return f"{obj.__class__.__name__}"


@receiver(post_save)
def log_create_or_update(sender, instance, created: bool, **kwargs):
    """Log create or update events."""
    # Skip excluded models
    model_name = sender.__name__
    if model_name in EXCLUDED_MODELS:
        return
    
    # Skip if this is a bulk operation
    if kwargs.get("raw", False):
        return
    
    # Get current user and request
    user = get_current_user()
    request = get_current_request()
    station = get_station_from_user(user)
    
    # Determine action
    action = AuditEvent.Action.CREATE if created else AuditEvent.Action.UPDATE
    
    # Get object representation
    object_repr = get_object_repr(instance)
    
    # Get metadata for updates
    metadata = {}
    if not created and hasattr(instance, "get_changes"):
        try:
            metadata["changes"] = instance.get_changes()
        except Exception:
            pass
    
    # Create audit event
    create_audit_event(
        action=action,
        object_type=model_name,
        object_id=instance.pk,
        object_repr=object_repr,
        actor=user,
        station=station,
        metadata=metadata,
        request=request,
    )


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Log delete events."""
    # Skip excluded models
    model_name = sender.__name__
    if model_name in EXCLUDED_MODELS:
        return
    
    # Skip if this is a bulk operation
    if kwargs.get("raw", False):
        return
    
    # Get current user and request
    user = get_current_user()
    request = get_current_request()
    station = get_station_from_user(user)
    
    # Get object representation
    object_repr = get_object_repr(instance)
    
    # Create audit event
    create_audit_event(
        action=AuditEvent.Action.DELETE,
        object_type=model_name,
        object_id=instance.pk,
        object_repr=object_repr,
        actor=user,
        station=station,
        metadata={"deleted": True},
        request=request,
    )


# Monkey-patch Django's request handling to store current request
# This is needed because signals don't have access to the request object
original_handle = None


def enable_audit_middleware():
    """Enable audit logging by patching Django's request handling."""
    global original_handle
    
    from django.core.handlers.wsgi import WSGIHandler
    
    if original_handle is None:
        original_handle = WSGIHandler.__call__
    
    def patched_handle(self, request):
        # Store current request in settings for signal access
        settings._current_request = request
        try:
            return original_handle(self, request)
        finally:
            # Clean up
            if hasattr(settings, "_current_request"):
                delattr(settings, "_current_request")
    
    WSGIHandler.__call__ = patched_handle


# Enable audit logging when this module is imported
enable_audit_middleware()

# Connect signals
post_save.connect(log_create_or_update)
post_delete.connect(log_delete)
