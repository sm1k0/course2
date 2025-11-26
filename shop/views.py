from decimal import Decimal
from datetime import timedelta
import csv
import io

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import (
    admin_required,
    is_admin,
    is_manager,
    is_operator,
    manager_required,
    operator_required,
)
from accounts.models import Role, UserSettings
from catalog.models import Product, Category, Stock, Supplier
from orders.models import Order, OrderItem
from .forms import (
    CategoryForm,
    LoginForm,
    OrderStatusForm,
    ProductForm,
    RegisterForm,
    StockForm,
    SupplierForm,
    UserRoleForm,
    UserSettingsForm,
)

User = get_user_model()


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

    settings_obj = None
    if request.user.is_authenticated:
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    saved_filters = getattr(settings_obj, 'saved_filters', {}) if settings_obj else {}
    if not category_id and not search and saved_filters:
        category_id = saved_filters.get('category')
        search = saved_filters.get('q')

    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')

    if category_id:
        products = products.filter(category_id=category_id)
    if search:
        products = products.filter(name__icontains=search)

    if settings_obj is not None:
        settings_obj.saved_filters = {
            'category': category_id or '',
            'q': search or '',
        }
        settings_obj.save(update_fields=['saved_filters'])

    cart = _get_cart(request)
    cart_items, cart_total = _cart_items(cart)

    page_size = 12
    if settings_obj:
        if 5 <= settings_obj.page_size <= 100:
            page_size = settings_obj.page_size

    paginator = Paginator(products, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'products': page_obj,
        'page_obj': page_obj,
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


# ====== Управление (management) ======


def _allowed_operator_transition(old, new):
    chain = {
        Order.Status.NEW: {Order.Status.ACCEPTED},
        Order.Status.ACCEPTED: {Order.Status.PREPARING, Order.Status.CANCELED},
        Order.Status.PREPARING: {Order.Status.PACKED, Order.Status.CANCELED},
        Order.Status.PACKED: {Order.Status.SHIPPED, Order.Status.READY_FOR_PICKUP, Order.Status.CANCELED},
        Order.Status.SHIPPED: {Order.Status.CANCELED, Order.Status.COMPLETED},
        Order.Status.READY_FOR_PICKUP: {Order.Status.CANCELED, Order.Status.COMPLETED},
    }
    return new in chain.get(old, set())


def _validate_transition(user, order, new_status):
    old_status = order.status
    def has_role(codes):
        return bool(getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) and user.role.code in codes)

    if has_role({'ADMIN'}) or has_role({'ADMIN', 'MANAGER'}):
        return True
    if has_role({'ADMIN', 'MANAGER', 'ORDER_OPERATOR'}):
        return _allowed_operator_transition(old_status, new_status)
    return False


@manager_required
def management_dashboard(request):
    products_count = Product.objects.count()
    orders_count = Order.objects.count()
    last_week = timezone.now() - timedelta(days=7)
    sales_last_week = (
        Order.objects.filter(created_at__gte=last_week)
        .aggregate(total=models.Sum('total_amount'))
        .get('total')
        or 0
    )
    return render(
        request,
        'shop/management/dashboard.html',
        {
            'products_count': products_count,
            'orders_count': orders_count,
            'sales_last_week': sales_last_week,
        },
    )


@manager_required
def management_products(request):
    products = Product.objects.select_related('category', 'supplier').all().order_by('name')
    return render(request, 'shop/management/products_list.html', {'products': products})


@manager_required
def management_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            Stock.objects.get_or_create(product=product)
            messages.success(request, 'Товар создан.')
            return redirect('shop:management_products')
    else:
        form = ProductForm()
    return render(request, 'shop/management/product_form.html', {'form': form, 'title': 'Создание товара'})


@manager_required
def management_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар обновлён.')
            return redirect('shop:management_products')
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        'shop/management/product_form.html',
        {'form': form, 'title': f'Редактирование товара #{product.id}'},
    )


@manager_required
def management_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.info(request, 'Товар удалён.')
        return redirect('shop:management_products')
    return render(request, 'shop/management/confirm_delete.html', {'object': product, 'type': 'товар'})


@manager_required
def management_categories(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'shop/management/categories_list.html', {'categories': categories})


@manager_required
def management_category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория создана.')
            return redirect('shop:management_categories')
    else:
        form = CategoryForm()
    return render(request, 'shop/management/category_form.html', {'form': form, 'title': 'Создание категории'})


@manager_required
def management_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория обновлена.')
            return redirect('shop:management_categories')
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        'shop/management/category_form.html',
        {'form': form, 'title': f'Редактирование категории #{category.id}'},
    )


@manager_required
def management_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.info(request, 'Категория удалена.')
        return redirect('shop:management_categories')
    return render(request, 'shop/management/confirm_delete.html', {'object': category, 'type': 'категорию'})


@manager_required
def management_suppliers(request):
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'shop/management/suppliers_list.html', {'suppliers': suppliers})


@manager_required
def management_supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Поставщик создан.')
            return redirect('shop:management_suppliers')
    else:
        form = SupplierForm()
    return render(request, 'shop/management/supplier_form.html', {'form': form, 'title': 'Создание поставщика'})


@manager_required
def management_supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Поставщик обновлён.')
            return redirect('shop:management_suppliers')
    else:
        form = SupplierForm(instance=supplier)
    return render(
        request,
        'shop/management/supplier_form.html',
        {'form': form, 'title': f'Редактирование поставщика #{supplier.id}'},
    )


@manager_required
def management_supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.info(request, 'Поставщик удалён.')
        return redirect('shop:management_suppliers')
    return render(request, 'shop/management/confirm_delete.html', {'object': supplier, 'type': 'поставщика'})


@manager_required
def management_stock(request):
    stock_items = Stock.objects.select_related('product').all().order_by('product__name')
    return render(request, 'shop/management/stock_list.html', {'stock_items': stock_items})


@manager_required
def management_stock_edit(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, 'Остаток обновлён.')
            return redirect('shop:management_stock')
    else:
        form = StockForm(instance=stock)
    return render(
        request,
        'shop/management/stock_form.html',
        {'form': form, 'title': f'Остаток для {stock.product.name}'},
    )


@operator_required
def management_orders(request):
    orders = (
        Order.objects.select_related('customer__user')
        .prefetch_related('items__product')
        .all()
        .order_by('-created_at')
    )
    return render(request, 'shop/management/orders_list.html', {'orders': orders})


@operator_required
def management_order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related('customer__user').prefetch_related('items__product'), pk=pk)
    form = OrderStatusForm(instance=order)
    return render(request, 'shop/management/order_detail.html', {'order': order, 'form': form})


@operator_required
def management_order_status(request, pk):
    order = get_object_or_404(Order.objects.select_related('customer__user').prefetch_related('items__product'), pk=pk)
    if request.method != 'POST':
        return redirect('shop:management_order_detail', pk=pk)
    form = OrderStatusForm(request.POST, instance=order)
    if not form.is_valid():
        messages.error(request, 'Некорректный статус.')
        return redirect('shop:management_order_detail', pk=pk)

    new_status = form.cleaned_data['status']
    if not _validate_transition(request.user, order, new_status):
        messages.error(request, 'Недостаточно прав для такого перехода статуса.')
        return redirect('shop:management_order_detail', pk=pk)

    with transaction.atomic():
        old_status = order.status
        if old_status == Order.Status.NEW and new_status == Order.Status.ACCEPTED:
            for item in order.items.select_related('product__stock'):
                stock = getattr(item.product, 'stock', None)
                if not stock or stock.quantity < item.quantity:
                    messages.error(request, f'Недостаточно товара {item.product.name} на складе.')
                    transaction.set_rollback(True)
                    return redirect('shop:management_order_detail', pk=pk)
            for item in order.items.select_related('product__stock'):
                stock = item.product.stock
                stock.quantity -= item.quantity
                stock.save(update_fields=['quantity'])

        if new_status == Order.Status.CANCELED and old_status != Order.Status.CANCELED:
            if old_status != Order.Status.NEW:
                for item in order.items.select_related('product__stock'):
                    stock = getattr(item.product, 'stock', None)
                    if stock:
                        stock.quantity += item.quantity
                        stock.save(update_fields=['quantity'])

        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

    messages.success(request, 'Статус заказа обновлён.')
    return redirect('shop:management_order_detail', pk=pk)


@admin_required
def management_users(request):
    users = User.objects.select_related('role').all().order_by('username')
    return render(request, 'shop/management/users_list.html', {'users': users})


@admin_required
def management_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Роль пользователя обновлена.')
            return redirect('shop:management_users')
    else:
        form = UserRoleForm(instance=user)
    return render(request, 'shop/management/user_form.html', {'form': form, 'title': f'Пользователь {user.username}'})


@manager_required
def management_products_import(request):
    report = None
    errors = []
    created = 0
    updated = 0
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        data = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(data))
        for idx, row in enumerate(reader, start=2):
            try:
                category, _ = Category.objects.get_or_create(name=row.get('category', 'Без категории'), defaults={'slug': row.get('category', '') or row.get('name', '')})
                supplier, _ = Supplier.objects.get_or_create(name=row.get('supplier', 'Неизвестный'))
                product, created_flag = Product.objects.update_or_create(
                    sku=row['sku'],
                    defaults={
                        'name': row.get('name', ''),
                        'category': category,
                        'supplier': supplier,
                        'price': Decimal(row.get('price') or '0'),
                        'discount_percent': int(row.get('discount_percent') or 0),
                        'is_active': True,
                    },
                )
                Stock.objects.get_or_create(product=product)
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f'Строка {idx}: {exc}')
        report = {'created': created, 'updated': updated, 'errors': errors}

    return render(request, 'shop/management/products_import.html', {'report': report})
