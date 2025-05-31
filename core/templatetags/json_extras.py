import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='parse_json')
def parse_json(value):
    """Parse a JSON string into a Python object."""
    if value is None or value == '':
        return []
    
    try:
        # First try to parse it as is
        return json.loads(value)
    except (ValueError, TypeError):
        try:
            # If that fails, try with string escaping/replacing
            # This handles Django's escaping of quotes
            value = value.replace('&quot;', '"').replace('&#39;', "'")
            return json.loads(value)
        except (ValueError, TypeError):
            # If all else fails, return an empty list
            return [] 