from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.catalog_view, name='catalog'),                 # каталог
    path('product/<int:pk>/', views.product_detail, name='product_detail'),  # детальная
    path('cart/', views.cart_view, name='cart'),                  # корзина
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
]

urlpatterns += [
    path('reports/', views.reports_view, name='reports'),
    path('settings/', views.settings_view, name='settings'),
    path('export/products/csv/', views.export_products_csv, name='export_products_csv'),
    path('export/sales/daily/csv/', views.export_sales_daily_csv, name='export_sales_daily_csv'),
]

urlpatterns += [
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('management/products/', views.management_products, name='management_products'),
    path('management/products/create/', views.management_product_create, name='management_product_create'),
    path('management/products/<int:pk>/edit/', views.management_product_edit, name='management_product_edit'),
    path('management/products/<int:pk>/delete/', views.management_product_delete, name='management_product_delete'),
    path('management/products/import/', views.management_products_import, name='management_products_import'),

    path('management/categories/', views.management_categories, name='management_categories'),
    path('management/categories/create/', views.management_category_create, name='management_category_create'),
    path('management/categories/<int:pk>/edit/', views.management_category_edit, name='management_category_edit'),
    path('management/categories/<int:pk>/delete/', views.management_category_delete, name='management_category_delete'),

    path('management/suppliers/', views.management_suppliers, name='management_suppliers'),
    path('management/suppliers/create/', views.management_supplier_create, name='management_supplier_create'),
    path('management/suppliers/<int:pk>/edit/', views.management_supplier_edit, name='management_supplier_edit'),
    path('management/suppliers/<int:pk>/delete/', views.management_supplier_delete, name='management_supplier_delete'),

    path('management/stock/', views.management_stock, name='management_stock'),
    path('management/stock/<int:pk>/edit/', views.management_stock_edit, name='management_stock_edit'),

    path('management/orders/', views.management_orders, name='management_orders'),
    path('management/orders/<int:pk>/', views.management_order_detail, name='management_order_detail'),
    path('management/orders/<int:pk>/status/', views.management_order_status, name='management_order_status'),

    path('management/users/', views.management_users, name='management_users'),
    path('management/users/<int:pk>/edit/', views.management_user_edit, name='management_user_edit'),
]
