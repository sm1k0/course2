from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'user',
        'table_name',
        'operation',
        'object_pk',
        'ip_address',
    )
    list_filter = ('operation', 'table_name', 'created_at')
    search_fields = (
        'table_name',
        'object_pk',
        'user__username',
        'user__email',
        'ip_address',
        'user_agent',
    )
    readonly_fields = (
        'user',
        'table_name',
        'operation',
        'object_pk',
        'data_before',
        'data_after',
        'ip_address',
        'user_agent',
        'created_at',
    )

    fieldsets = (
        (None, {
            'fields': (
                'created_at',
                'user',
                'table_name',
                'operation',
                'object_pk',
            )
        }),
        ('Данные', {
            'fields': (
                'data_before',
                'data_after',
            )
        }),
        ('Техническая информация', {
            'fields': (
                'ip_address',
                'user_agent',
            )
        }),
    )
