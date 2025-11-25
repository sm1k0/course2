from django import template
from django.utils import timezone
from django.utils.formats import date_format as django_date_format

from accounts.models import UserSettings

register = template.Library()


@register.filter
def format_date(value, user_settings=None):
    if not value:
        return ''

    date_format = None
    if user_settings and getattr(user_settings, 'date_format', None):
        date_format = user_settings.date_format
    if not date_format:
        date_format = UserSettings.DateFormat.DMY

    value = timezone.localtime(value) if timezone.is_aware(value) else value
    return django_date_format(value, date_format)
