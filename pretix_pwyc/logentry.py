from django.utils.translation import gettext_lazy as _
from pretix.base.models import LogEntry


def log_item_pwyc_enabled(event, user, item):
    """Log when PWYC is enabled for an item"""
    return LogEntry.objects.create(
        event=event,
        action_type='pretix_pwyc.item.enabled',
        user=user,
        content_object=item,
        data={
            'id': item.pk,
            'name': str(item)
        }
    )


def log_item_pwyc_disabled(event, user, item):
    """Log when PWYC is disabled for an item"""
    return LogEntry.objects.create(
        event=event,
        action_type='pretix_pwyc.item.disabled',
        user=user,
        content_object=item,
        data={
            'id': item.pk,
            'name': str(item)
        }
    )


def log_price_changed(event, position, original_price, custom_price):
    """Log when a custom price is used"""
    return LogEntry.objects.create(
        event=event,
        action_type='pretix_pwyc.order.price_changed',
        content_object=position,
        data={
            'position': position.pk,
            'item': str(position.item),
            'original_price': str(original_price),
            'price': str(custom_price)
        }
    )
