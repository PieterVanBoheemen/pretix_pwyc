from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from pretix.control.views.event import EventSettingsViewMixin
from .forms import PWYCSettingsForm

logger = logging.getLogger(__name__)


class PWYCSettingsView(EventSettingsViewMixin, FormView):
    template_name = 'pretix_pwyc/settings.html'
    form_class = PWYCSettingsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['obj'] = self.request.event
        kwargs['attribute_name'] = 'settings'
        kwargs['locales'] = self.request.event.settings.locales
        return kwargs

    def get_success_url(self):
        return reverse('plugins:pretix_pwyc:settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug,
        })

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Your settings have been saved.'))
        return super().form_valid(form)


@method_decorator(csrf_exempt, name='dispatch')
class PWYCSetPriceView(View):
    """AJAX view to set custom price in session"""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            price = data.get('price')

            if not item_id or price is None:
                return JsonResponse({'error': 'Missing item_id or price'}, status=400)

            # Validate price
            try:
                price = float(price)
                if price < 0:
                    return JsonResponse({'error': 'Price cannot be negative'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid price format'}, status=400)

            # Store in session
            session_key = f'pwyc_price_{item_id}'
            request.session[session_key] = str(price)
            request.session.modified = True

            logger.info(f"PWYC: Set custom price {price} for item {item_id} in session")

            return JsonResponse({'success': True, 'price': price})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"PWYC: Error setting price: {e}")
            return JsonResponse({'error': 'Internal error'}, status=500)
