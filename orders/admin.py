from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ('product',)
    readonly_fields = ('created_at',)
    fields = ('product', 'quantity', 'unit_price', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'status',
        'total_amount',
        'payment_method',
        'delivery_method',
        'created_at',
        'assigned_operator',
    )
    list_filter = (
        'status',
        'payment_method',
        'delivery_method',
        'created_at',
    )
    search_fields = (
        'id',
        'customer__full_name',
        'customer__user__username',
        'delivery_address',
    )
    autocomplete_fields = ('customer', 'created_by', 'assigned_operator')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'unit_price', 'line_total', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__id', 'product__name', 'product__sku')
    autocomplete_fields = ('order', 'product')
    readonly_fields = ('created_at',)
