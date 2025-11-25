from django import template
from django.utils import formats

register = template.Library()


@register.filter
def format_date(value, user_settings=None):
    if not value:
        return ''

    date_format = None
    if user_settings and getattr(user_settings, 'date_format', None):
        date_format = user_settings.date_format

    date_format = date_format or formats.get_format('DATE_FORMAT')
    try:
        return value.strftime(date_format.replace('Y', '%Y').replace('m', '%m').replace('d', '%d'))
    except Exception:
        return value
