from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Category(models.Model):
    """
    Таблица categories — категории товаров.
    Теперь с изображением категории.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Название категории',
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name='Слаг (URL)',
        help_text='Генерируется автоматически из названия.',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )

    # 📌 Новое: изображение категории
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        verbose_name='Изображение категории'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создана',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлена',
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        db_table = 'categories'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Supplier(models.Model):
    """
    Таблица suppliers — поставщики.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Название поставщика',
    )
    contact_email = models.EmailField(
        max_length=255,
        blank=True,
        verbose_name='Email',
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Телефон',
    )
    address = models.CharField(
        max_length=512,
        blank=True,
        verbose_name='Адрес',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
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
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        db_table = 'suppliers'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Таблица products — товары.
    Теперь с изображением товара.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Название товара',
    )
    sku = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Артикул (SKU)',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория',
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Поставщик',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Цена',
        help_text='Должна быть > 0',
    )
    discount_percent = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Скидка, %',
    )

    # 📌 Новое: изображение товара
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name='Изображение товара'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
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
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        db_table = 'products'
        ordering = ('name',)
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gt=0),
                name='product_price_gt_0',
            ),
            models.CheckConstraint(
                check=models.Q(discount_percent__gte=0) & models.Q(discount_percent__lte=100),
                name='product_discount_0_100',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.sku})'

    @property
    def final_price(self):
        if self.discount_percent:
            return self.price * (100 - self.discount_percent) / 100
        return self.price


class Stock(models.Model):
    """
    Таблица stock — складские остатки.
    """
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock',
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Количество',
    )
    warehouse_location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Расположение на складе',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено',
    )

    class Meta:
        verbose_name = 'Складской остаток'
        verbose_name_plural = 'Складские остатки'
        db_table = 'stock'
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='stock_quantity_gte_0',
            ),
        ]

    def __str__(self):
        return f'Остаток {self.product.name}: {self.quantity}'
