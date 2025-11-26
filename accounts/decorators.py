from functools import wraps
from typing import Iterable

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

ALLOWED_ADMIN = {'ADMIN'}
ALLOWED_MANAGER = {'ADMIN', 'MANAGER'}
ALLOWED_OPERATOR = {'ADMIN', 'MANAGER', 'ORDER_OPERATOR'}


def _user_has_role(user, roles: Iterable[str]) -> bool:
    return bool(getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) and user.role.code in roles)


def role_required(*role_codes: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not _user_has_role(request.user, role_codes):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def is_admin(view_func=None):
    decorator = role_required('ADMIN')
    return decorator(view_func) if view_func else decorator


def is_manager(view_func=None):
    decorator = role_required('ADMIN', 'MANAGER')
    return decorator(view_func) if view_func else decorator


def is_operator(view_func=None):
    decorator = role_required('ADMIN', 'MANAGER', 'ORDER_OPERATOR')
    return decorator(view_func) if view_func else decorator


def admin_test(user):
    return _user_has_role(user, ALLOWED_ADMIN)


def manager_test(user):
    return _user_has_role(user, ALLOWED_MANAGER)


def operator_test(user):
    return _user_has_role(user, ALLOWED_OPERATOR)


def admin_required(view_func):
    return user_passes_test(admin_test)(view_func)


def manager_required(view_func):
    return user_passes_test(manager_test)(view_func)


def operator_required(view_func):
    return user_passes_test(operator_test)(view_func)
