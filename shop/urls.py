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
