from decimal import Decimal
from django.dispatch import receiver
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from pretix.base.signals import (
    register_global_settings, event_copy_data, item_copy_data,
    logentry_display, register_payment_providers,
    item_forms, validate_cart_addons, validate_cart,
    order_info
)
from pretix.presale.signals import (
    checkout_confirm_messages, checkout_flow_steps,
    fee_calculation_for_cart, order_meta_from_request
)
from pretix.control.signals import nav_event_settings, item_formsets

from pretix.base.models import LogEntry
from .forms import PWYCSettingsForm, PWYCItemForm, PWYCPriceForm


def is_pwyc_item(event, item):
    """Helper to check if an item is PWYC-enabled"""
    return event.settings.get(f'pwyc_enabled_{item.pk}', False)


@receiver(register_global_settings, dispatch_uid="pretix_pwyc_global_settings")
def register_global_settings(sender, **kwargs):
    return {
        'pwyc_explanation_default': '',
    }


@receiver(item_formsets, dispatch_uid="pretix_pwyc_item_formset")
def pwyc_formset(sender, request, item, **kwargs):
    """Add PWYC form to item edit page"""
    form = PWYCItemForm(
        prefix='pwyc',
        event=sender,
        item=item,
        data=request.POST if request.method == 'POST' else None,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()

    template = get_template('pretix_pwyc/item_edit_pwyc.html')
    return {
        'title': _('Pay What You Can'),
        'form': form,
        'template': template,
    }


@receiver(nav_event_settings, dispatch_uid='pretix_pwyc_nav_settings')
def add_settings_tab(sender, request, **kwargs):
    """Add PWYC settings tab to event settings"""
    return [{
        'label': _('Pay What You Can'),
        'url': '/control/event/{}/{}/settings/pwyc/'.format(sender.organizer.slug, sender.slug),
        'active': request.path.endswith('/settings/pwyc/'),
    }]


@receiver(validate_cart_addons, dispatch_uid="pretix_pwyc_validate_addons")
def validate_pwyc_price_addons(sender, addons, base_position, iao, request, **kwargs):
    """
    Handle price input during cart addon additions
    """
    item = base_position.item

    if not is_pwyc_item(sender, item):
        return

    price_key = f'pwyc_price_{item.pk}'
    if price_key in request.POST:
        price = request.POST.get(price_key)
        try:
            price = Decimal(price)
        except (ValueError, TypeError):
            from pretix.presale.checkoutflow import CartError
            raise CartError(_("Please enter a valid price."))

        # Validate minimum price
        min_price = sender.settings.get(f'pwyc_min_amount_{item.pk}')
        if min_price and price < Decimal(min_price):
            from pretix.presale.checkoutflow import CartError
            raise CartError(_("The price must be at least {min_price}.").format(min_price=min_price))

        # Store in session
        session_key = f'pwyc_price_{item.pk}'
        request.session[session_key] = str(price)


@receiver(validate_cart, dispatch_uid="pretix_pwyc_validate_cart")
def validate_pwyc_price(sender, positions, request, **kwargs):
    """
    Handle price input during normal cart additions
    """
    from pretix.presale.checkoutflow import CartError

    for pos in positions:
        item = pos.item

        if not is_pwyc_item(sender, item):
            continue

        price_key = f'pwyc_price_{item.pk}'
        if price_key in request.POST:
            price = request.POST.get(price_key)
            try:
                price = Decimal(price)
            except (ValueError, TypeError):
                raise CartError(_("Please enter a valid price."))

            # Validate minimum price
            min_price = sender.settings.get(f'pwyc_min_amount_{item.pk}')
            if min_price and price < Decimal(min_price):
                raise CartError(_("The price must be at least {min_price}.").format(min_price=min_price))

            # Store in session
            session_key = f'pwyc_price_{item.pk}'
            request.session[session_key] = str(price)


@receiver(fee_calculation_for_cart, dispatch_uid="pretix_pwyc_fee_calculation")
def apply_pwyc_price(sender, positions, invoice_address, meta_info, total, payment_requests, request, **kwargs):
    """
    Apply custom prices to cart positions
    """
    for pos in positions:
        if is_pwyc_item(sender, pos.item):
            session_key = f'pwyc_price_{pos.item.pk}'
            if request and session_key in request.session:
                price = Decimal(request.session[session_key])

                # Store original price in meta_info for reference
                meta_info = pos.meta_info or {}
                meta_info['pwyc_original_price'] = str(pos.price)
                pos.meta_info = meta_info

                # Set the new price
                pos.price = price

    return []  # No additional fees


@receiver(order_meta_from_request, dispatch_uid="pretix_pwyc_order_meta")
def pwyc_order_meta(sender, request, **kwargs):
    """
    Store PWYC information in order metadata
    """
    meta = {}

    # Find all pwyc session keys
    if request:
        for key in request.session.keys():
            if key.startswith('pwyc_price_'):
                meta[key] = request.session[key]

    return meta


@receiver(order_info, dispatch_uid="pretix_pwyc_order_info")
def pwyc_order_info(sender, order, request, **kwargs):
    """
    Display PWYC information on order detail page
    """
    pwyc_positions = []

    for p in order.positions.all():
        if p.meta_info and 'pwyc_original_price' in p.meta_info:
            pwyc_positions.append(p)

    if not pwyc_positions:
        return

    template = get_template('pretix_pwyc/order_info.html')
    return template.render({
        'positions': pwyc_positions,
    })


@receiver(logentry_display, dispatch_uid="pretix_pwyc_logentry_display")
def pwyc_logentry_display(sender, logentry, **kwargs):
    """
    Display human-readable log entries
    """
    if logentry.action_type.startswith('pretix_pwyc'):
        if logentry.action_type == 'pretix_pwyc.item.enabled':
            return _('Pay What You Can was enabled for item "{item}"').format(
                item=logentry.content_object or _('Unknown')
            )
        elif logentry.action_type == 'pretix_pwyc.item.disabled':
            return _('Pay What You Can was disabled for item "{item}"').format(
                item=logentry.content_object or _('Unknown')
            )
        elif logentry.action_type == 'pretix_pwyc.order.price_changed':
            data = logentry.parsed_data
            return _('Custom price of {price} was set for item "{item}"').format(
                price=data.get('price', '?'),
                item=data.get('item', _('Unknown'))
            )

    return None


@receiver(item_forms, dispatch_uid="pretix_pwyc_item_forms")
def pwyc_item_forms(sender, item, request, **kwargs):
    """
    Add PWYC price form to product page
    """
    if not is_pwyc_item(sender, item):
        return []

    # Get configuration
    min_price = sender.settings.get(f'pwyc_min_amount_{item.pk}')
    suggested_price = sender.settings.get(f'pwyc_suggested_amount_{item.pk}')

    # Create form
    initial = {}
    if suggested_price:
        initial['pwyc_price'] = suggested_price

    form = PWYCPriceForm(
        item=item,
        min_price=min_price,
        suggested_price=suggested_price,
        prefix=f'pwyc_{item.pk}',
        data=request.POST if request.method == 'POST' else None,
        initial=initial
    )

    template = get_template('pretix_pwyc/price_form.html')
    return [{
        'form': form,
        'template': template,
        'explanation': sender.settings.get(f'pwyc_explanation_{item.pk}'),
    }]


@receiver(event_copy_data, dispatch_uid='pretix_pwyc_copy_data')
def event_copy_data_receiver(sender, other, item_map, **kwargs):
    """
    Copy PWYC settings when copying an event
    """
    for old_item_id, new_item in item_map.items():
        if other.settings.get(f'pwyc_enabled_{old_item_id}'):
            sender.settings.set(f'pwyc_enabled_{new_item.pk}', True)
            sender.settings.set(
                f'pwyc_min_amount_{new_item.pk}',
                other.settings.get(f'pwyc_min_amount_{old_item_id}')
            )
            sender.settings.set(
                f'pwyc_suggested_amount_{new_item.pk}',
                other.settings.get(f'pwyc_suggested_amount_{old_item_id}')
            )
            sender.settings.set(
                f'pwyc_explanation_{new_item.pk}',
                other.settings.get(f'pwyc_explanation_{old_item_id}')
            )

    sender.settings.set('pwyc_explanation_default', other.settings.get('pwyc_explanation_default', ''))


@receiver(item_copy_data, dispatch_uid='pretix_pwyc_copy_item_data')
def item_copy_data_receiver(sender, source, target, **kwargs):
    """
    Copy PWYC settings when copying an item
    """
    if sender.settings.get(f'pwyc_enabled_{source.pk}'):
        sender.settings.set(f'pwyc_enabled_{target.pk}', True)
        sender.settings.set(
            f'pwyc_min_amount_{target.pk}',
            sender.settings.get(f'pwyc_min_amount_{source.pk}')
        )
        sender.settings.set(
            f'pwyc_suggested_amount_{target.pk}',
            sender.settings.get(f'pwyc_suggested_amount_{source.pk}')
        )
        sender.settings.set(
            f'pwyc_explanation_{target.pk}',
            sender.settings.get(f'pwyc_explanation_{source.pk}')
        )
