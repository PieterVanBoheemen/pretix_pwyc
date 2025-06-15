from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PluginApp(AppConfig):
    name = 'pretix_pwyc'
    verbose_name = _('Pay What You Can')

    class PretixPluginMeta:
        name = _('Pay What You Can')
        author = _('Pieter van Boheemen')
        description = _('Allows customers to choose their own price for tickets')
        visible = True
        version = '1.0.0'
        category = 'FEATURE'
        compatibility = "pretix>=4.0.0"

    def ready(self):
        from . import signals  # noqa


default_app_config = 'pretix_pwyc.PluginApp'
