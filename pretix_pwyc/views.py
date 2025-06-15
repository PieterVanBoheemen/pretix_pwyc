from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from pretix.control.views.event import EventSettingsViewMixin
from .forms import PWYCSettingsForm


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
