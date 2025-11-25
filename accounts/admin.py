from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Role, User, CustomerProfile, UserSettings


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')
    search_fields = ('code', 'name')


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Ролевые настройки', {'fields': ('role', 'is_blocked')}),
    )
    list_display = ('username', 'email', 'role', 'is_active', 'is_blocked', 'is_staff')
    list_filter = ('role', 'is_active', 'is_blocked', 'is_staff')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'phone', 'created_at')
    search_fields = ('full_name', 'user__username', 'phone')


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'theme', 'language', 'date_format')
