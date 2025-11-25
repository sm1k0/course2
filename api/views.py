from django.contrib.auth import authenticate
from django.db.models import Sum, F, Count

from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdminOrManagerOrReadOnly, IsAdminOrManager
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
)
from catalog.models import Category, Product, Stock
from orders.models import Order, OrderItem


# ========= AUTH =========

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response(
                {'detail': 'Неверный логин или пароль.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token.key,
            }
        )


# ========= КАТЕГОРИИ / ТОВАРЫ =========

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrManagerOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'supplier')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrManagerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()

        category_id = self.request.query_params.get('category')
        search = self.request.query_params.get('search')

        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(name__icontains=search)

        return qs


# ========= ЗАКАЗЫ =========

class OrderViewSet(viewsets.ModelViewSet):
    """
    /api/orders/

    - Покупатель (CUSTOMER) видит и создаёт только свои заказы.
    - ADMIN / MANAGER / ORDER_OPERATOR видят все заказы.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not getattr(user, 'role', None):
            return Order.objects.none()

        code = user.role.code

        if code in ('ADMIN', 'MANAGER', 'ORDER_OPERATOR'):
            return (
                Order.objects
                .select_related('customer', 'assigned_operator')
                .prefetch_related('items')
            )

        # CUSTOMER — только свои
        if code == 'CUSTOMER' and hasattr(user, 'customer_profile'):
            return (
                Order.objects
                .filter(customer=user.customer_profile)
                .select_related('customer')
                .prefetch_related('items')
            )

        return Order.objects.none()

    def perform_create(self, serializer):
        # created_by и логика берутся внутри сериализатора
        serializer.save()


# ========= ОТЧЁТЫ / АНАЛИТИКА =========

class SalesByDayView(ListAPIView):
    """
    GET /api/reports/sales/daily/
    Продажи по дням: дата, сумма, кол-во заказов.
    """
    permission_classes = [IsAdminOrManager]

    def get(self, request, *args, **kwargs):
        qs = (
            Order.objects
            .filter(status=Order.Status.COMPLETED)
            .values('created_at__date')
            .annotate(
                total_amount=Sum('total_amount'),
                orders_count=Count('id'),
            )
            .order_by('created_at__date')
        )

        data = [
            {
                'date': row['created_at__date'],
                'total_amount': row['total_amount'],
                'orders_count': row['orders_count'],
            }
            for row in qs
        ]
        return Response(data)


class SalesByCategoryView(ListAPIView):
    """
    GET /api/reports/sales/by-category/
    Продажи по категориям: категория, сумма, кол-во проданных единиц.
    """
    permission_classes = [IsAdminOrManager]

    def get(self, request, *args, **kwargs):
        qs = (
            OrderItem.objects
            .filter(order__status=Order.Status.COMPLETED)
            .values('product__category__id', 'product__category__name')
            .annotate(
                total_amount=Sum(F('unit_price') * F('quantity')),
                total_quantity=Sum('quantity'),
            )
            .order_by('product__category__name')
        )

        data = [
            {
                'category_id': row['product__category__id'],
                'category_name': row['product__category__name'],
                'total_amount': row['total_amount'],
                'total_quantity': row['total_quantity'],
            }
            for row in qs
        ]
        return Response(data)


class StockReportView(ListAPIView):
    """
    GET /api/reports/stock/
    Отчёт по остаткам: товар, категория, количество на складе.
    """
    permission_classes = [IsAdminOrManager]

    def get(self, request, *args, **kwargs):
        qs = (
            Stock.objects
            .select_related('product', 'product__category')
            .values(
                'product__id',
                'product__name',
                'product__sku',
                'product__category__name',
                'quantity',
            )
            .order_by('product__name')
        )

        data = [
            {
                'product_id': row['product__id'],
                'product_name': row['product__name'],
                'sku': row['product__sku'],
                'category_name': row['product__category__name'],
                'quantity': row['quantity'],
            }
            for row in qs
        ]
        return Response(data)
