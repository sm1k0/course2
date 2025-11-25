from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrManagerOrReadOnly(BasePermission):
    """
    GET/HEAD/OPTIONS — всем авторизованным.
    POST/PUT/PATCH/DELETE — только ADMIN или MANAGER.
    """

    def has_permission(self, request, view):
        user = request.user

        # чтение — любому авторизованному
        if request.method in SAFE_METHODS:
            return user.is_authenticated

        # запись — только если есть роль и она ADMIN / MANAGER
        if not user.is_authenticated or not getattr(user, 'role', None):
            return False

        return user.role.code in ('ADMIN', 'MANAGER')


class IsAdminOrManager(BasePermission):
    """
    Для отчётов / аналитики.
    Доступ только ADMIN и MANAGER.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or not getattr(user, 'role', None):
            return False
        return user.role.code in ('ADMIN', 'MANAGER')
