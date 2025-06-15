from decimal import Decimal
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
import logging

# Import only the signals we know exist in pretix core
from pretix.base.signals import (
    register_global_settings, event_copy_data, item_copy_data,
    logentry_display
)
from pretix.presale.signals import (
    fee_calculation_for_cart, order_meta_from_request
)
from pretix.control.signals import nav_event_settings, item_formsets

from pretix.base.models import LogEntry
from .forms import PWYCSettingsForm, PWYCItemForm, PWYCPriceForm

logger = logging.getLogger(__name__)


def is_pwyc_item(event, item):
    """Helper to check if an item is PWYC-enabled"""
    try:
        return bool(event.settings.get(f'pwyc_enabled_{item.pk}', False))
    except:
        return False


@receiver(register_global_settings, dispatch_uid="pretix_pwyc_global_settings")
def register_global_settings_receiver(sender, **kwargs):
    return {
        'pwyc_explanation_default': '',
    }


@receiver(item_formsets, dispatch_uid="pretix_pwyc_item_formset")
def pwyc_formset(sender, request, item, **kwargs):
    """Add PWYC form to item edit page"""
    try:
        # Very simple implementation to avoid any string operation issues
        return {
            'title': 'Pay What You Can',
            'content': '''
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">Pay What You Can</h3>
                </div>
                <div class="panel-body">
                    <div class="form-group">
                        <div class="checkbox">
                            <label>
                                <input type="checkbox" name="pwyc-pwyc_enabled">
                                Enable Pay What You Can
                            </label>
                            <p class="help-block">Allow customers to choose their own price for this item</p>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="id_pwyc-pwyc_min_amount">Minimum amount</label>
                        <input type="number" step="0.01" name="pwyc-pwyc_min_amount" class="form-control" id="id_pwyc-pwyc_min_amount">
                        <p class="help-block">Minimum amount customers must pay. Leave empty for no minimum.</p>
                    </div>
                    <div class="form-group">
                        <label for="id_pwyc-pwyc_suggested_amount">Suggested amount</label>
                        <input type="number" step="0.01" name="pwyc-pwyc_suggested_amount" class="form-control" id="id_pwyc-pwyc_suggested_amount">
                        <p class="help-block">Suggested amount displayed to customers.</p>
                    </div>
                    <div class="form-group">
                        <label for="id_pwyc-pwyc_explanation">Explanation text</label>
                        <textarea name="pwyc-pwyc_explanation" class="form-control" rows="3" id="id_pwyc-pwyc_explanation"></textarea>
                        <p class="help-block">Text explaining the PWYC option to customers.</p>
                    </div>
                </div>
            </div>
            ''',
        }
    except Exception as e:
        logger.error(f"PWYC: Error in item formset: {e}")
        return {
            'title': 'Pay What You Can',
            'content': '<div class="alert alert-danger">Error loading Pay What You Can settings.</div>',
        }


@receiver(nav_event_settings, dispatch_uid='pretix_pwyc_nav_settings')
def add_settings_tab(sender, request, **kwargs):
    """Add PWYC settings tab to event settings"""
    try:
        # Very simple implementation
        return [{
            'label': 'Pay What You Can',
            'url': f'/control/event/{sender.organizer.slug}/{sender.slug}/settings/pwyc/',
            'active': False,  # Simplified - just always false for now
        }]
    except Exception as e:
        logger.error(f"PWYC: Error in nav settings: {e}")
        return []


@receiver(fee_calculation_for_cart, dispatch_uid="pretix_pwyc_fee_calculation")
def apply_pwyc_price(sender, positions, invoice_address, meta_info, total, payment_requests, request, **kwargs):
    """
    Apply custom prices to cart positions
    """
    try:
        for pos in positions:
            if is_pwyc_item(sender, pos.item):
                session_key = f'pwyc_price_{pos.item.pk}'
                if request and hasattr(request, 'session') and session_key in request.session:
                    try:
                        price = Decimal(str(request.session[session_key]))

                        # Store original price in meta_info for reference
                        if not hasattr(pos, 'meta_info') or pos.meta_info is None:
                            pos.meta_info = {}
                        pos.meta_info['pwyc_original_price'] = str(pos.price)

                        # Set the new price
                        pos.price = price
                        logger.info(f"PWYC: Applied custom price {price} to item {pos.item.pk}")
                    except Exception as e:
                        logger.error(f"PWYC: Error applying price for item {pos.item.pk}: {e}")

        return []  # No additional fees
    except Exception as e:
        logger.error(f"PWYC: Error in fee calculation: {e}")
        return []


@receiver(order_meta_from_request, dispatch_uid="pretix_pwyc_order_meta")
def pwyc_order_meta(sender, request, **kwargs):
    """
    Store PWYC information in order metadata
    """
    try:
        meta = {}

        # Find all pwyc session keys
        if request and hasattr(request, 'session'):
            for key in request.session.keys():
                key_str = str(key)
                if key_str.startswith('pwyc_price_'):
                    meta[key] = request.session[key]

        return meta
    except Exception as e:
        logger.error(f"PWYC: Error in order meta: {e}")
        return {}


@receiver(logentry_display, dispatch_uid="pretix_pwyc_logentry_display")
def pwyc_logentry_display(sender, logentry, **kwargs):
    """
    Display human-readable log entries
    """
    try:
        action_type_str = str(logentry.action_type) if hasattr(logentry, 'action_type') else ''

        if action_type_str.startswith('pretix_pwyc'):
            if action_type_str == 'pretix_pwyc.item.enabled':
                return f'Pay What You Can was enabled for item "{logentry.content_object or "Unknown"}"'
            elif action_type_str == 'pretix_pwyc.item.disabled':
                return f'Pay What You Can was disabled for item "{logentry.content_object or "Unknown"}"'
            elif action_type_str == 'pretix_pwyc.order.price_changed':
                data = getattr(logentry, 'parsed_data', {})
                return f'Custom price of {data.get("price", "?")} was set for item "{data.get("item", "Unknown")}"'

        return None
    except Exception as e:
        logger.error(f"PWYC: Error in log display: {e}")
        return None


@receiver(event_copy_data, dispatch_uid='pretix_pwyc_copy_data')
def event_copy_data_receiver(sender, other, item_map, **kwargs):
    """
    Copy PWYC settings when copying an event
    """
    try:
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
    except Exception as e:
        logger.error(f"PWYC: Error in event copy: {e}")


@receiver(item_copy_data, dispatch_uid='pretix_pwyc_copy_item_data')
def item_copy_data_receiver(sender, source, target, **kwargs):
    """
    Copy PWYC settings when copying an item
    """
    try:
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
    except Exception as e:
        logger.error(f"PWYC: Error in item copy: {e}")


# TODO: Implement customer-facing price input form
# This will need to be done through template overrides or custom views
# since the item_forms signal doesn't exist in this version of pretix
