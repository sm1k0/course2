from decimal import Decimal
import csv
import io

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django import forms
from accounts.models import UserSettings
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.models import Product, Category, Stock
from orders.models import Order, OrderItem
from .forms import LoginForm, RegisterForm


# ====== Вспомогательные функции для корзины ======

CART_SESSION_KEY = 'cart'


def _get_cart(request):
    """
    Корзина хранится в сессии как словарь:
    { product_id: quantity }
    """
    return request.session.get(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _cart_items(cart):
    """
    Преобразуем {id: qty} -> список объектов с продуктом и суммой.
    """
    product_ids = cart.keys()
    products = Product.objects.filter(id__in=product_ids, is_active=True).select_related('category')
    products_map = {p.id: p for p in products}

    items = []
    total = Decimal('0.00')

    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = products_map.get(pid)
        if not product:
            continue
        quantity = int(qty)
        line_total = product.final_price * quantity
        total += line_total
        items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total,
        })

    return items, total


# ====== Вьюхи магазина ======

def catalog_view(request):
    category_id = request.GET.get('category')
    search = request.GET.get('q')

    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')

    if category_id:
        products = products.filter(category_id=category_id)
    if search:
        products = products.filter(name__icontains=search)

    cart = _get_cart(request)
    cart_items, cart_total = _cart_items(cart)

    context = {
        'categories': categories,
        'products': products,
        'current_category_id': int(category_id) if category_id else None,
        'search_query': search or '',
        'cart_total': cart_total,
        'cart_count': sum(item['quantity'] for item in cart_items),
    }
    return render(request, 'shop/catalog.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk, is_active=True)

    cart = _get_cart(request)
    cart_items, cart_total = _cart_items(cart)

    context = {
        'product': product,
        'cart_total': cart_total,
        'cart_count': sum(item['quantity'] for item in cart_items),
    }
    return render(request, 'shop/product_detail.html', context)


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    cart = _get_cart(request)
    current_qty = int(cart.get(str(product.id), 0))
    new_qty = current_qty + 1

    # проверяем остаток
    stock = getattr(product, 'stock', None)
    if stock and new_qty > stock.quantity:
        messages.error(request, f'Недостаточно товара "{product.name}" на складе.')
        return redirect('shop:catalog')

    cart[str(product.id)] = new_qty
    _save_cart(request, cart)

    messages.success(request, f'Товар "{product.name}" добавлен в корзину.')
    return redirect(request.META.get('HTTP_REFERER', 'shop:catalog'))


def cart_remove(request, product_id):
    cart = _get_cart(request)
    pid = str(product_id)
    if pid in cart:
        cart.pop(pid)
        _save_cart(request, cart)
        messages.info(request, 'Товар удалён из корзины.')
    return redirect('shop:cart')


def cart_view(request):
    cart = _get_cart(request)
    items, total = _cart_items(cart)

    context = {
        'items': items,
        'total': total,
    }
    return render(request, 'shop/cart.html', context)


@login_required
def checkout_view(request):
    cart = _get_cart(request)
    items, total = _cart_items(cart)

    if not items:
        messages.error(request, 'Корзина пуста.')
        return redirect('shop:catalog')

    profile = getattr(request.user, 'customer_profile', None)

    if request.method == 'POST':
        delivery_address = request.POST.get('delivery_address') or (profile.default_address if profile else '')
        comment = request.POST.get('comment', '')

        # создаём заказ
        order = Order.objects.create(
            customer=profile,
            status=Order.Status.NEW,
            payment_method='CARD_ONLINE',
            delivery_method='COURIER',
            delivery_address=delivery_address,
            comment=comment,
            total_amount=0,
            created_by=request.user,
        )

        # позиции + списание склада
        total_amount = Decimal('0.00')

        for item in items:
            product = item['product']
            quantity = item['quantity']

            stock = getattr(product, 'stock', None)
            if not stock or stock.quantity < quantity:
                messages.error(request, f'Недостаточно товара "{product.name}" на складе.')
                order.delete()
                return redirect('shop:cart')

            stock.quantity -= quantity
            stock.save(update_fields=['quantity'])

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.final_price,
            )

            total_amount += product.final_price * quantity

        order.total_amount = total_amount
        order.save(update_fields=['total_amount'])

        # очищаем корзину
        _save_cart(request, {})

        messages.success(request, 'Заказ успешно оформлен!')
        return redirect('shop:order_success', order_id=order.id)

    context = {
        'items': items,
        'total': total,
        'profile': profile,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user.customer_profile)
    return render(request, 'shop/order_success.html', {'order': order})


# ====== Аутентификация ======

def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:catalog')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.user)
            messages.success(request, 'Вы успешно вошли в систему.')
            return redirect('shop:catalog')
    else:
        form = LoginForm()

    return render(request, 'shop/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('shop:catalog')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('shop:catalog')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно.')
            return redirect('shop:catalog')
    else:
        form = RegisterForm()

    return render(request, 'shop/auth/register.html', {'form': form})


@login_required
def profile_view(request):
    profile = getattr(request.user, 'customer_profile', None)
    orders = Order.objects.filter(customer=profile).order_by('-created_at') if profile else []

    return render(request, 'shop/profile.html', {
        'profile': profile,
        'orders': orders,
    })


# ====== Отчёты, настройки, экспорт ======


def is_admin_or_manager(user):
    return bool(getattr(user, 'role', None) and user.role.code in ('ADMIN', 'MANAGER'))


@user_passes_test(is_admin_or_manager)
def export_products_csv(request):
    products = (
        Product.objects
        .select_related('category')
        .annotate(stock_quantity=Coalesce(F('stock__quantity'), Value(0)))
        .order_by('name')
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'id',
        'name',
        'sku',
        'category',
        'price',
        'discount_percent',
        'is_active',
        'stock_quantity',
    ])

    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.sku,
            product.category.name if product.category else '',
            product.price,
            product.discount_percent,
            product.is_active,
            product.stock_quantity,
        ])

    filename = f"products_{timezone.now().date()}.csv"
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@user_passes_test(is_admin_or_manager)
def export_sales_daily_csv(request):
    sales = (
        Order.objects
        .filter(status=Order.Status.COMPLETED)
        .values('created_at__date')
        .annotate(
            total_amount=models.Sum('total_amount'),
            orders_count=models.Count('id'),
        )
        .order_by('created_at__date')
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['date', 'total_amount', 'orders_count'])

    for row in sales:
        writer.writerow([
            row['created_at__date'],
            row['total_amount'],
            row['orders_count'],
        ])

    filename = f"sales_daily_{timezone.now().date()}.csv"
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def reports_view(request):
    context = {
        'sales_daily_url': '/api/reports/sales/daily/',
        'sales_by_category_url': '/api/reports/sales/by-category/',
        'stock_url': '/api/reports/stock/',
    }
    return render(request, 'shop/reports.html', context)


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['theme', 'language', 'date_format', 'page_size']


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки успешно сохранены.')
            return redirect('shop:settings')
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, 'shop/settings.html', {'form': form})
