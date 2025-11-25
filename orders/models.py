from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import CustomerProfile
from catalog.models import Product


User = settings.AUTH_USER_MODEL


class Order(models.Model):
    """
    Таблица orders — заказы.
    """

    class Status(models.TextChoices):
        NEW = 'NEW', 'Новый'
        ACCEPTED = 'ACCEPTED', 'Принят'
        PREPARING = 'PREPARING', 'Готовится'
        PACKED = 'PACKED', 'Упакован'
        SHIPPED = 'SHIPPED', 'Передан в доставку'
        READY_FOR_PICKUP = 'READY_FOR_PICKUP', 'Готов к выдаче'
        COMPLETED = 'COMPLETED', 'Завершён'
        CANCELED = 'CANCELED', 'Отменён'

    class PaymentMethod(models.TextChoices):
        CARD_ONLINE = 'CARD_ONLINE', 'Карта онлайн'
        CARD_ON_DELIVERY = 'CARD_ON_DELIVERY', 'Карта при получении'
        CASH = 'CASH', 'Наличные'

    class DeliveryMethod(models.TextChoices):
        PICKUP = 'PICKUP', 'Самовывоз'
        COURIER = 'COURIER', 'Курьер'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Покупатель',
    )

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус заказа',
    )

    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD_ONLINE,
        verbose_name='Способ оплаты',
    )

    delivery_method = models.CharField(
        max_length=32,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.COURIER,
        verbose_name='Способ доставки',
    )

    delivery_address = models.CharField(
        max_length=512,
        verbose_name='Адрес доставки',
    )

    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий покупателя',
    )

    # Кто создал / принял / ведёт заказ (менеджер/оператор)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders',
        verbose_name='Создан сотрудником',
        help_text='Менеджер или оператор, оформивший заказ',
    )

    assigned_operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        verbose_name='Оператор заказов',
        help_text='Сотрудник, обрабатывающий заказ',
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма заказа',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлён',
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        db_table = 'orders'
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name='order_total_amount_gte_0',
            ),
        ]

    def __str__(self):
        return f'Заказ #{self.id} от {self.customer.full_name} ({self.get_status_display()})'

    def recalc_total(self, save: bool = True):
        """
        Пересчитать сумму заказа по позициям.
        Это нам пригодится в sp_create_order / сервисах.
        """
        total = sum(item.line_total for item in self.items.all())
        self.total_amount = total
        if save:
            self.save(update_fields=['total_amount'])
        return total


class OrderItem(models.Model):
    """
    Таблица order_items — состав заказа.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Количество',
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Цена за единицу',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано',
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        db_table = 'order_items'
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=1),
                name='order_item_quantity_gte_1',
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gt=0),
                name='order_item_unit_price_gt_0',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} x {self.quantity} (заказ #{self.order_id})'

    @property
    def line_total(self):
        return self.unit_price * self.quantity
