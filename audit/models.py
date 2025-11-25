from django.conf import settings
from django.db import models


User = settings.AUTH_USER_MODEL


class AuditLog(models.Model):
    """
    Таблица audit_log — журнал аудита.

    Требования ТЗ:
    - user_id
    - дата/время
    - операция
    - таблица
    - данные до/после
    """

    class Operation(models.TextChoices):
        CREATE = 'CREATE', 'Создание'
        UPDATE = 'UPDATE', 'Изменение'
        DELETE = 'DELETE', 'Удаление'
        LOGIN = 'LOGIN', 'Вход в систему'
        OTHER = 'OTHER', 'Другое'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Пользователь',
    )

    table_name = models.CharField(
        max_length=128,
        verbose_name='Таблица',
        help_text='Имя таблицы/модели, над которой выполнялась операция.',
    )

    operation = models.CharField(
        max_length=16,
        choices=Operation.choices,
        verbose_name='Операция',
    )

    object_pk = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='ID объекта',
        help_text='Первичный ключ записи (если есть).',
    )

    # JSON-поля для данных до/после (Django 5.2 — стандартный JSONField)
    data_before = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Данные до',
    )

    data_after = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Данные после',
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP-адрес',
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='User-Agent',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время операции',
    )

    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        db_table = 'audit_log'
        ordering = ('-created_at',)

    def __str__(self):
        return f'[{self.created_at}] {self.operation} {self.table_name} (id={self.object_pk})'


# Небольшой хелпер, чтобы проще писать в журнал из кода / вьюх
def write_audit_log(
    *,
    user=None,
    table_name: str,
    operation: str,
    object_pk: str | int | None = None,
    data_before=None,
    data_after=None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> "AuditLog":
    """
    Удобная функция для записи в audit_log из кода (API / сервисов).
    Можно будет вызывать, например, при изменении заказа или товара.
    """
    if object_pk is not None:
        object_pk = str(object_pk)

    return AuditLog.objects.create(
        user=user,
        table_name=table_name,
        operation=operation,
        object_pk=object_pk or '',
        data_before=data_before,
        data_after=data_after,
        ip_address=ip_address,
        user_agent=user_agent or '',
    )
