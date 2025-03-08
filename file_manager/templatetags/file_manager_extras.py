
from django import template
register = template.Library()


def percentage_of(value, max_value):
    """Calculate what percentage of max_value is value"""
    try:
        return round((float(value) / float(max_value)) * 100, 2)
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def endswith(value, arg):
    """Check if value ends with argument"""
    return value.endswith(arg)
from django import template
register = template.Library()

@register.filter
def percentage_of(value, max_value):
    """Calculate what percentage of max_value is value"""
    try:
        return min(100, round((float(value) / float(max_value)) * 100))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def filesizeformat(bytes):
    """Format the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB, 102 bytes, etc)."""
    try:
        bytes = float(bytes)
    except (TypeError, ValueError, UnicodeDecodeError):
        return "0 bytes"

    if bytes < 1024:
        return f"{bytes:.0f} bytes"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.1f} GB"

@register.filter
def endswith(value, arg):
    """Check if value ends with argument"""
    return value.endswith(arg)

