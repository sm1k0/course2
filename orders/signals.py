from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Order
from audit.models import write_audit_log
from audit.utils import serialize_instance


@receiver(pre_save, sender=Order)
def order_before_update(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_state = None
        return

    try:
        old = sender.objects.get(pk=instance.pk)
        instance._old_state = old
    except sender.DoesNotExist:
        instance._old_state = None


@receiver(post_save, sender=Order)
def order_after_save(sender, instance, created, **kwargs):
    operation = 'CREATE' if created else 'UPDATE'

    data_before = serialize_instance(getattr(instance, '_old_state', None))
    data_after = serialize_instance(instance)

    write_audit_log(
        user=None,
        table_name='orders',
        operation=operation,
        object_pk=instance.pk,
        data_before=data_before,
        data_after=data_after,
    )


@receiver(post_delete, sender=Order)
def order_after_delete(sender, instance, **kwargs):
    data_before = serialize_instance(instance)

    write_audit_log(
        user=None,
        table_name='orders',
        operation='DELETE',
        object_pk=instance.pk,
        data_before=data_before,
        data_after=None,
    )
