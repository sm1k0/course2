from types import SimpleNamespace

from accounts.models import UserSettings


def user_settings(request):
    """Provide user settings for templates with sensible defaults."""
    default_values = {
        'theme': UserSettings.Theme.LIGHT,
        'language': 'ru',
        'date_format': UserSettings.DateFormat.DMY,
        'page_size': UserSettings.PageSize.MEDIUM,
        'saved_filters': {},
    }

    if request.user.is_authenticated:
        settings_obj, _ = UserSettings.objects.get_or_create(
            user=request.user,
            defaults=default_values,
        )
        return {'user_settings': settings_obj}

    return {'user_settings': SimpleNamespace(**default_values)}
