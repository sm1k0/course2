from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    """
    Таблица roles — ролевая модель:
    - ADMIN
    - MANAGER
    - ORDER_OPERATOR
    - CUSTOMER
    """
    class RoleCode(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        MANAGER = 'MANAGER', 'Менеджер'
        ORDER_OPERATOR = 'ORDER_OPERATOR', 'Оператор заказов'
        CUSTOMER = 'CUSTOMER', 'Покупатель'

    code = models.CharField(
        max_length=32,
        unique=True,
        choices=RoleCode.choices,
        verbose_name='Код роли',
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Название роли',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )

    def __str__(self) -> str:
        return f'{self.name} ({self.code})'

    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
        db_table = 'roles'


class User(AbstractUser):
    """
    Таблица users — все аккаунты.
    Наследуемся от AbstractUser, добавляем связь с Role.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Роль',
    )

    # При желании можно добавить поле "is_blocked" и т.п.
    is_blocked = models.BooleanField(
        default=False,
        verbose_name='Заблокирован',
    )

    def __str__(self) -> str:
        return f'{self.username} ({self.role.code if self.role else "NO_ROLE"})'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        db_table = 'users'
class CustomerProfile(models.Model):
    """
    Таблица customers — профиль клиента (покупателя).
    Внешний ключ на User, у которого роль CUSTOMER.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        verbose_name='Пользователь',
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name='ФИО',
    )
    phone = models.CharField(
        max_length=32,
        verbose_name='Телефон',
    )
    # Email уже есть в User.email

    default_address = models.CharField(
        max_length=512,
        blank=True,
        verbose_name='Адрес по умолчанию',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлён',
    )

    def __str__(self) -> str:
        return f'Профиль {self.user.username}'

    class Meta:
        verbose_name = 'Профиль покупателя'
        verbose_name_plural = 'Профили покупателей'
        db_table = 'customers'


class UserSettings(models.Model):
    """
    user_settings — настройки интерфейса (тема, язык, формат дат).
    """
    class Theme(models.TextChoices):
        LIGHT = 'light', 'Светлая'
        DARK = 'dark', 'Тёмная'

    class DateFormat(models.TextChoices):
        DMY = 'd.m.Y', 'ДД.ММ.ГГГГ'
        YMD = 'Y-m-d', 'ГГГГ-ММ-ДД'

    class PageSize(models.IntegerChoices):
        SMALL = 10, '10'
        MEDIUM = 20, '20'
        LARGE = 50, '50'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='Пользователь',
    )
    theme = models.CharField(
        max_length=16,
        choices=Theme.choices,
        default=Theme.LIGHT,
        verbose_name='Тема',
    )
    language = models.CharField(
        max_length=8,
        default='ru',
        verbose_name='Язык',
    )
    date_format = models.CharField(
        max_length=16,
        choices=DateFormat.choices,
        default=DateFormat.DMY,
        verbose_name='Формат даты',
    )
    page_size = models.PositiveIntegerField(
        choices=PageSize.choices,
        default=PageSize.MEDIUM,
        verbose_name='Размер страницы',
    )

    def __str__(self) -> str:
        return f'Настройки {self.user.username}'

    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'
        db_table = 'user_settings'
