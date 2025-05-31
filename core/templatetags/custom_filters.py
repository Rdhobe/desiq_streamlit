from django import template
from django.templatetags.static import static as django_static
from django.conf import settings
import os

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def addclass(field, css_class):
    """Add a CSS class to a form field."""
    return field.as_widget(attrs={"class": css_class})

@register.filter
def jsonify(obj):
    """Convert an object to JSON string (safe for use in JavaScript)."""
    import json
    return json.dumps(obj)

@register.simple_tag
def robust_static(path):
    """
    A more robust version of the static tag that handles missing files gracefully.
    
    If the static file is missing from the manifest:
    1. It tries to use Django's built-in static tag
    2. If that fails, it falls back to a direct URL construction
    
    Usage: {% robust_static 'css/style.css' %}
    """
    try:
        # First try Django's regular static tag
        return django_static(path)
    except Exception:
        # Fallback to direct URL construction
        return f"{settings.STATIC_URL}{path}"

@register.simple_tag
def static_direct(path):
    """
    Return a direct URL to a static file without using the manifest.
    Useful when you're having issues with the staticfiles manifest.
    
    Usage: {% static_direct 'css/style.css' %}
    """
    return f"{settings.STATIC_URL}{path}" 