# familyview_project/templatetags/child_filters.py
from django import template

register = template.Library()

@register.filter
def has_child_profile(user):
    return hasattr(user, 'child_profile')
