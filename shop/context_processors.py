from types import SimpleNamespace

from accounts.models import UserSettings


DEFAULT_SETTINGS = {
    'theme': UserSettings.Theme.LIGHT,
    'language': 'ru',
    'date_format': UserSettings.DateFormat.DMY,
    'page_size': UserSettings.PageSize.MEDIUM,
    'saved_filters': {},
}


def user_settings(request):
    """Provide user settings to templates with sensible defaults."""
    if request.user.is_authenticated:
        settings_obj, _ = UserSettings.objects.get_or_create(
            user=request.user,
            defaults=DEFAULT_SETTINGS,
        )
        return {'user_settings': settings_obj}

    return {'user_settings': SimpleNamespace(**DEFAULT_SETTINGS)}
