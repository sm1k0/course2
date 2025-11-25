from django.contrib import admin
from .models import Category, Supplier, Product, Stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'created_at', 'updated_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contact_email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_email', 'phone')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'sku',
        'category',
        'supplier',
        'price',
        'discount_percent',
        'is_active',
        'created_at',
    )
    list_filter = ('category', 'supplier', 'is_active', 'created_at')
    search_fields = ('name', 'sku', 'description')
    autocomplete_fields = ('category', 'supplier')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'warehouse_location', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('product__name', 'product__sku', 'warehouse_location')
    autocomplete_fields = ('product',)
    readonly_fields = ('updated_at',)
