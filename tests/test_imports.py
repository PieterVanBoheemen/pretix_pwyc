from unittest import TestCase
from pretix_pwyc.forms import PWYCSettingsForm, PWYCItemForm, PWYCPriceForm


def test_imports():
    """Test that all imports work correctly"""
    import pretix_pwyc
    import pretix_pwyc.forms
    import pretix_pwyc.signals
    import pretix_pwyc.views
    import pretix_pwyc.urls
    import pretix_pwyc.logentry
