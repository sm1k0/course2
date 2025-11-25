from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from accounts.models import CustomerProfile, Role, UserSettings
from catalog.models import Category, Product
from orders.models import Order, OrderItem

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.code', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')


class RegisterSerializer(serializers.Serializer):
    """
    Регистрация покупателя (CUSTOMER).
    """
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32)
    address = serializers.CharField(max_length=512, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Такой логин уже занят.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Такой email уже зарегистрирован.')
        return value

    def create(self, validated_data):
        role_customer = Role.objects.get(code='CUSTOMER')

        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            role=role_customer,
        )
        user.set_password(validated_data['password'])
        user.save()

        CustomerProfile.objects.create(
            user=user,
            full_name=validated_data['full_name'],
            phone=validated_data['phone'],
            default_address=validated_data.get('address', ''),
        )

        UserSettings.objects.create(
            user=user,
            theme=UserSettings.Theme.LIGHT,
            language='ru',
        )

        return user


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'image',
        )


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
    )

    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'sku',
            'category',
            'category_id',
            'description',
            'price',
            'discount_percent',
            'image',
            'is_active',
            'created_at',
        )
        read_only_fields = ('created_at',)


# ====== ЗАКАЗЫ ======

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
    )
    product = ProductSerializer(read_only=True)
    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_id',
            'quantity',
            'unit_price',
            'line_total',
            'created_at',
        )
        read_only_fields = ('id', 'product', 'line_total', 'created_at')


class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    # для создания/обновления
    items_data = OrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = (
            'id',
            'customer',
            'status',
            'status_display',
            'payment_method',
            'delivery_method',
            'delivery_address',
            'comment',
            'total_amount',
            'created_at',
            'updated_at',
            'items',
            'items_data',
        )
        read_only_fields = ('total_amount', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        # customer может создавать только свои заказы
        if request and request.method == 'POST' and user and getattr(user, 'role', None):
            if user.role.code == 'CUSTOMER':
                # customer не должен сам передавать customer в body
                attrs.pop('customer', None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        items_data = validated_data.pop('items_data', [])

        # определяем customer
        customer = validated_data.get('customer')
        if not customer:
            # если заказ создаёт CUSTOMER — берём его профиль
            if hasattr(user, 'customer_profile'):
                customer = user.customer_profile
            else:
                raise serializers.ValidationError('Нельзя определить покупателя для заказа.')

        order = Order.objects.create(
            customer=customer,
            payment_method=validated_data.get('payment_method'),
            delivery_method=validated_data.get('delivery_method'),
            delivery_address=validated_data.get('delivery_address'),
            comment=validated_data.get('comment', ''),
            created_by=user if user and user.is_authenticated else None,
        )

        # создаём позиции заказа
        from catalog.models import Stock  # локальный импорт, чтобы не словить циклы

        for item in items_data:
            product: Product = item['product']
            quantity = item['quantity']

            # берём цену с учётом скидки
            unit_price = product.final_price

            # проверяем остатки
            stock = getattr(product, 'stock', None)
            if not stock or stock.quantity < quantity:
                raise serializers.ValidationError(
                    f'Недостаточно товара "{product.name}" на складе.'
                )

            # уменьшаем остаток
            stock.quantity -= quantity
            stock.save(update_fields=['quantity'])

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
            )

        order.recalc_total(save=True)
        return order
