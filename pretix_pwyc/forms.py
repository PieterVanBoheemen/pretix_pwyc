from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SettingsForm


class PWYCSettingsForm(SettingsForm):
    """
    Settings form for global PWYC plugin settings
    """
    pwyc_explanation_default = forms.CharField(
        label=_('Default explanation text'),
        required=False,
        widget=forms.Textarea,
        help_text=_('Default text explaining the PWYC option to customers.'),
    )


class PWYCItemForm(forms.Form):
    """
    Form for per-item PWYC configuration
    """
    pwyc_enabled = forms.BooleanField(
        label=_('Enable Pay What You Can'),
        required=False,
        help_text=_('Allow customers to choose their own price for this item')
    )

    pwyc_min_amount = forms.DecimalField(
        label=_('Minimum amount'),
        required=False,
        min_value=0,
        help_text=_('Minimum amount customers must pay. Leave empty for no minimum.'),
        validators=[MinValueValidator(0)]
    )

    pwyc_suggested_amount = forms.DecimalField(
        label=_('Suggested amount'),
        required=False,
        min_value=0,
        help_text=_('Suggested amount displayed to customers.'),
        validators=[MinValueValidator(0)]
    )

    pwyc_explanation = forms.CharField(
        label=_('Explanation text'),
        required=False,
        widget=forms.Textarea,
        help_text=_('Text explaining the PWYC option to customers.')
    )

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event')
        self.item = kwargs.pop('item')
        super().__init__(*args, **kwargs)

        if self.item and self.item.pk:
            self.initial['pwyc_enabled'] = self.event.settings.get(f'pwyc_enabled_{self.item.pk}', False)
            self.initial['pwyc_min_amount'] = self.event.settings.get(f'pwyc_min_amount_{self.item.pk}')
            self.initial['pwyc_suggested_amount'] = self.event.settings.get(f'pwyc_suggested_amount_{self.item.pk}')
            self.initial['pwyc_explanation'] = self.event.settings.get(
                f'pwyc_explanation_{self.item.pk}',
                self.event.settings.get('pwyc_explanation_default', '')
            )

    def save(self):
        if not self.item or not self.item.pk:
            return

        self.event.settings.set(f'pwyc_enabled_{self.item.pk}', self.cleaned_data.get('pwyc_enabled', False))
        self.event.settings.set(f'pwyc_min_amount_{self.item.pk}', self.cleaned_data.get('pwyc_min_amount'))
        self.event.settings.set(f'pwyc_suggested_amount_{self.item.pk}', self.cleaned_data.get('pwyc_suggested_amount'))
        self.event.settings.set(f'pwyc_explanation_{self.item.pk}', self.cleaned_data.get('pwyc_explanation'))


class PWYCItemSettingsForm(forms.Form):
    """
    Individual form for PWYC item settings - for use in formsets
    """

    pwyc_enabled = forms.BooleanField(
        label=_('Enable Pay What You Can'),
        required=False,
        help_text=_('Allow customers to choose their own price for this item')
    )

    pwyc_min_amount = forms.DecimalField(
        label=_('Minimum amount'),
        required=False,
        min_value=0,
        help_text=_('Minimum amount customers must pay. Leave empty for no minimum.'),
        validators=[MinValueValidator(0)]
    )

    pwyc_suggested_amount = forms.DecimalField(
        label=_('Suggested amount'),
        required=False,
        min_value=0,
        help_text=_('Suggested amount displayed to customers.'),
        validators=[MinValueValidator(0)]
    )

    pwyc_explanation = forms.CharField(
        label=_('Explanation text'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=_('Text explaining the PWYC option to customers.')
    )

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.item = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)

        # Load existing values
        if self.event and self.item and self.item.pk:
            if not self.data:  # Only set initial values if no form data
                self.initial['pwyc_enabled'] = self.event.settings.get(f'pwyc_enabled_{self.item.pk}', False)
                self.initial['pwyc_min_amount'] = self.event.settings.get(f'pwyc_min_amount_{self.item.pk}')
                self.initial['pwyc_suggested_amount'] = self.event.settings.get(f'pwyc_suggested_amount_{self.item.pk}')
                self.initial['pwyc_explanation'] = self.event.settings.get(
                    f'pwyc_explanation_{self.item.pk}',
                    self.event.settings.get('pwyc_explanation_default', '')
                )

    def save(self):
        """Save form data to event settings"""
        if not self.event or not self.item or not self.item.pk:
            return

        self.event.settings.set(f'pwyc_enabled_{self.item.pk}', self.cleaned_data.get('pwyc_enabled', False))
        self.event.settings.set(f'pwyc_min_amount_{self.item.pk}', self.cleaned_data.get('pwyc_min_amount'))
        self.event.settings.set(f'pwyc_suggested_amount_{self.item.pk}', self.cleaned_data.get('pwyc_suggested_amount'))
        self.event.settings.set(f'pwyc_explanation_{self.item.pk}', self.cleaned_data.get('pwyc_explanation'))


class PWYCPriceForm(forms.Form):
    """
    Form for customers to enter custom price
    """
    pwyc_price = forms.DecimalField(
        required=True,
        min_value=0,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )

    def __init__(self, *args, **kwargs):
        self.min_price = kwargs.pop('min_price', None)
        self.suggested_price = kwargs.pop('suggested_price', None)
        self.item = kwargs.pop('item')

        super().__init__(*args, **kwargs)

        field_label = _('Choose your price')

        if self.suggested_price:
            field_label = _('Choose your price (suggested: {suggested_price})').format(
                suggested_price=self.suggested_price
            )

        self.fields['pwyc_price'].label = field_label

        if self.min_price:
            self.fields['pwyc_price'].min_value = self.min_price
            self.fields['pwyc_price'].validators = [MinValueValidator(self.min_price)]
            self.fields['pwyc_price'].help_text = _('Minimum price: {min_price}').format(
                min_price=self.min_price
            )

    def clean_pwyc_price(self):
        price = self.cleaned_data['pwyc_price']
        if self.min_price and price < self.min_price:
            raise forms.ValidationError(
                _('The price must be at least {min_price}.').format(
                    min_price=self.min_price
                )
            )
        return price
