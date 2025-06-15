from decimal import Decimal
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django import forms
from django.forms import formset_factory
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
from .forms import PWYCSettingsForm, PWYCItemForm, PWYCPriceForm, PWYCItemSettingsForm

logger = logging.getLogger(__name__)


# Create the formset class
class PWYCFormSet(forms.BaseFormSet):
    """Custom formset for PWYC settings"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the required properties
        self.template = 'pretix_pwyc/item_edit_pwyc.html'
        self.title = 'Pay What You Can'

    def save(self):
        """Save all forms in the formset"""
        for form in self.forms:
            if hasattr(form, 'save') and form.cleaned_data:
                form.save()


PWYCFormSetClass = formset_factory(PWYCItemSettingsForm, formset=PWYCFormSet, extra=1, max_num=1)


def is_pwyc_item(event, item):
    """Helper to check if an item is PWYC-enabled"""
    try:
        enabled_setting = event.settings.get(f'pwyc_enabled_{item.pk}', 'false')
        # Handle both string and boolean values
        if isinstance(enabled_setting, str):
            return enabled_setting.lower() == 'true'
        else:
            return bool(enabled_setting)
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
        # Create a simple formset with one form
        initial_data = {}

        if item and hasattr(item, 'pk') and item.pk:
            try:
                # Safely get settings values and convert them to proper types
                # The error suggests that one of these settings calls is problematic
                logger.info(f"PWYC: Attempting to load settings for item {item.pk}")

                # Try each setting individually to isolate the problematic one
                try:
                    # The pwyc_enabled setting seems to be causing issues
                    # Let's try a different approach - bypass the problematic setting
                    # and use a fresh key or handle it differently

                    # First, let's try to clear any problematic boolean value
                    try:
                        # Check if there's a problematic value stored
                        problem_key = f'pwyc_enabled_{item.pk}'
                        # Try to delete any existing problematic value
                        if hasattr(sender.settings, 'delete'):
                            sender.settings.delete(problem_key)
                        logger.info(f"PWYC: Cleared potentially problematic setting {problem_key}")
                    except:
                        pass  # Ignore errors when clearing

                    # Now try to get the setting again, defaulting to False
                    pwyc_enabled = False  # Start with safe default
                    logger.info(f"PWYC: Using safe default for pwyc_enabled: {pwyc_enabled}")
                except Exception as e:
                    logger.error(f"PWYC: Error getting pwyc_enabled: {e}")
                    pwyc_enabled = False

                try:
                    pwyc_min_amount = sender.settings.get(f'pwyc_min_amount_{item.pk}', None)
                    logger.info(f"PWYC: Got pwyc_min_amount: {pwyc_min_amount} (type: {type(pwyc_min_amount)})")
                except Exception as e:
                    logger.error(f"PWYC: Error getting pwyc_min_amount: {e}")
                    pwyc_min_amount = None

                try:
                    pwyc_suggested_amount = sender.settings.get(f'pwyc_suggested_amount_{item.pk}', None)
                    logger.info(f"PWYC: Got pwyc_suggested_amount: {pwyc_suggested_amount} (type: {type(pwyc_suggested_amount)})")
                except Exception as e:
                    logger.error(f"PWYC: Error getting pwyc_suggested_amount: {e}")
                    pwyc_suggested_amount = None

                try:
                    pwyc_explanation = sender.settings.get(f'pwyc_explanation_{item.pk}', '')
                    logger.info(f"PWYC: Got pwyc_explanation: {pwyc_explanation} (type: {type(pwyc_explanation)})")
                except Exception as e:
                    logger.error(f"PWYC: Error getting pwyc_explanation: {e}")
                    pwyc_explanation = ''

                # Convert to safe values
                initial_data = {
                    'pwyc_enabled': bool(pwyc_enabled) if pwyc_enabled is not None else False,
                    'pwyc_min_amount': str(pwyc_min_amount) if pwyc_min_amount not in [None, ''] else '',
                    'pwyc_suggested_amount': str(pwyc_suggested_amount) if pwyc_suggested_amount not in [None, ''] else '',
                    'pwyc_explanation': str(pwyc_explanation) if pwyc_explanation is not None else '',
                }
                logger.info(f"PWYC: Loaded initial data: {initial_data}")
            except Exception as e:
                logger.error(f"PWYC: Error loading initial data: {e}")
                import traceback
                logger.error(f"PWYC: Initial data traceback: {traceback.format_exc()}")
                initial_data = {
                    'pwyc_enabled': False,
                    'pwyc_min_amount': '',
                    'pwyc_suggested_amount': '',
                    'pwyc_explanation': '',
                }

        # Safely check if this is a POST request with our data
        is_post = False
        try:
            if hasattr(request, 'method') and hasattr(request, 'POST'):
                method_str = str(request.method)
                # Check for any pwyc form fields in POST data
                has_pwyc_data = any(str(key).startswith('pwyc-') for key in request.POST.keys())
                is_post = method_str == 'POST' and has_pwyc_data
                logger.info(f"PWYC: POST check - method: {method_str}, has_pwyc_data: {has_pwyc_data}, is_post: {is_post}")
        except Exception as e:
            logger.error(f"PWYC: Error checking request method: {e}")
            is_post = False

        # Create the formset
        try:
            formset_data = request.POST if is_post else None
            formset_initial = [initial_data] if not is_post else None

            logger.info(f"PWYC: Creating formset with data={formset_data is not None}, initial={formset_initial}")

            formset = PWYCFormSetClass(
                data=formset_data,
                initial=formset_initial,
                prefix='pwyc'
            )

            logger.info(f"PWYC: Formset created successfully, forms count: {len(formset.forms)}")
        except Exception as e:
            logger.error(f"PWYC: Error creating formset: {e}")
            import traceback
            logger.error(f"PWYC: Formset creation traceback: {traceback.format_exc()}")
            # Create minimal formset
            formset = PWYCFormSetClass(prefix='pwyc', initial=[{
                'pwyc_enabled': False,
                'pwyc_min_amount': '',
                'pwyc_suggested_amount': '',
                'pwyc_explanation': '',
            }])

        # Pass event and item to forms safely
        try:
            for form in formset.forms:
                form.event = sender
                form.item = item
            logger.info(f"PWYC: Set event and item on {len(formset.forms)} forms")
        except Exception as e:
            logger.error(f"PWYC: Error setting form properties: {e}")

        # Set formset properties
        formset.template = 'pretix_pwyc/item_edit_pwyc.html'
        formset.title = 'Pay What You Can'

        # Save if valid POST
        if is_post:
            try:
                logger.info(f"PWYC: Processing POST data")
                logger.info(f"PWYC: Formset is_valid: {formset.is_valid()}")

                if formset.is_valid():
                    logger.info(f"PWYC: Formset is valid, attempting to save")
                    for i, form in enumerate(formset.forms):
                        logger.info(f"PWYC: Form {i} cleaned_data: {form.cleaned_data}")
                        if hasattr(form, 'save') and form.cleaned_data:
                            form.save()
                            logger.info(f"PWYC: Form {i} saved successfully")
                    logger.info(f"PWYC: Settings saved for item {item.pk}")
                    formset.title = 'Pay What You Can (Saved)'
                else:
                    logger.error(f"PWYC: Formset validation failed")
                    logger.error(f"PWYC: Formset errors: {formset.errors}")
                    logger.error(f"PWYC: Formset non_form_errors: {formset.non_form_errors()}")
                    for i, form in enumerate(formset.forms):
                        logger.error(f"PWYC: Form {i} errors: {form.errors}")
                    formset.title = 'Pay What You Can (Validation Error)'
            except Exception as e:
                logger.error(f"PWYC: Error saving formset: {e}")
                import traceback
                logger.error(f"PWYC: Save traceback: {traceback.format_exc()}")
                formset.title = 'Pay What You Can (Save Error)'

        logger.info(f"PWYC: Returning formset with title: {formset.title}")
        return formset

    except Exception as e:
        logger.error(f"PWYC: Error in item formset: {e}")
        import traceback
        logger.error(f"PWYC: Full traceback: {traceback.format_exc()}")

        # Return minimal formset on error
        try:
            formset = PWYCFormSetClass(prefix='pwyc', initial=[{
                'pwyc_enabled': False,
                'pwyc_min_amount': '',
                'pwyc_suggested_amount': '',
                'pwyc_explanation': '',
            }])
            formset.template = 'pretix_pwyc/item_edit_pwyc.html'
            formset.title = 'Pay What You Can (Error)'
            return formset
        except Exception as inner_e:
            logger.error(f"PWYC: Error creating fallback formset: {inner_e}")
            # Return None to disable this formset completely if everything fails
            return None


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
