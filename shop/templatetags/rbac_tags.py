from django import template

register = template.Library()


@register.filter
def is_admin(user):
    return bool(getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) and user.role.code == 'ADMIN')


@register.filter
def is_manager(user):
    return bool(
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'role', None)
        and user.role.code in {'ADMIN', 'MANAGER'}
    )


@register.filter
def is_operator(user):
    return bool(
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'role', None)
        and user.role.code in {'ADMIN', 'MANAGER', 'ORDER_OPERATOR'}
    )
