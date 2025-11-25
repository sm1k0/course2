from django.forms.models import model_to_dict


def serialize_instance(instance, exclude_fields=None):
    """
    Превращаем модель в dict для записи в audit_log.
    """
    if instance is None:
        return None

    exclude_fields = exclude_fields or []
    data = model_to_dict(instance)
    # технические поля можно убрать
    for field in ['password', 'last_login']:
        data.pop(field, None)
    for f in exclude_fields:
        data.pop(f, None)
    return data
