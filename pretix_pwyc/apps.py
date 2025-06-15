from django.utils.translation import gettext_lazy as _

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 4.0 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = 'pretix_pwyc'
    verbose_name = _('Pay What You Can')

    class PretixPluginMeta:
        name = _('Pay What You Can')
        author = _('Pieter van Boheemen')
        description = _('Allows customers to choose their own price for tickets')
        visible = True
        version = '0.0.9'
        category = 'FEATURE'
        compatibility = "pretix>=4.0.0"

    def ready(self):
        from . import signals  # noqa


default_app_config = 'pretix_pwyc.PluginApp'
