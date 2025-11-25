from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    RegisterView,
    CategoryViewSet,
    ProductViewSet,
    OrderViewSet,
    SalesByDayView,
    SalesByCategoryView,
    StockReportView,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),

    # отчёты / аналитика
    path('reports/sales/daily/', SalesByDayView.as_view(), name='report-sales-daily'),
    path('reports/sales/by-category/', SalesByCategoryView.as_view(), name='report-sales-by-category'),
    path('reports/stock/', StockReportView.as_view(), name='report-stock'),

    path('', include(router.urls)),
]
