from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Product
from audit.models import write_audit_log
from audit.utils import serialize_instance


@receiver(pre_save, sender=Product)
def product_before_update(sender, instance, **kwargs):
    if not instance.pk:
        # новый объект — до ещё нечего логировать
        instance._old_state = None
        return

    try:
        old = sender.objects.get(pk=instance.pk)
        instance._old_state = old
    except sender.DoesNotExist:
        instance._old_state = None


@receiver(post_save, sender=Product)
def product_after_save(sender, instance, created, **kwargs):
    # user, ip, user_agent из request тут не доступны (это уровень модели),
    # поэтому пишем только техническую инфу.
    operation = 'CREATE' if created else 'UPDATE'

    data_before = serialize_instance(getattr(instance, '_old_state', None))
    data_after = serialize_instance(instance)

    write_audit_log(
        user=None,  # можно оставить None, т.к. тут нет request
        table_name='products',
        operation=operation,
        object_pk=instance.pk,
        data_before=data_before,
        data_after=data_after,
    )


@receiver(post_delete, sender=Product)
def product_after_delete(sender, instance, **kwargs):
    data_before = serialize_instance(instance)

    write_audit_log(
        user=None,
        table_name='products',
        operation='DELETE',
        object_pk=instance.pk,
        data_before=data_before,
        data_after=None,
    )
