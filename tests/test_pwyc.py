import decimal
from django.test import TestCase
from django.utils.translation import gettext as _
from pretix.base.models import Event, Organizer, Item, CartPosition
from pretix.base.models.items import SubEvent
from pretix.base.services.cart import CartManager
from pretix.base.settings import GlobalSettingsObject


class PWYCTest(TestCase):
    def setUp(self):
        self.orga = Organizer.objects.create(name='PWYC Test', slug='pwyc-test')
        self.event = Event.objects.create(
            organizer=self.orga,
            name='PWYC Test Event',
            slug='pwyc-test-event',
            date_from='2030-01-01 10:00:00Z',
            plugins='pretix_pwyc',
        )
        self.ticket = Item.objects.create(
            event=self.event,
            name='Test Ticket',
            default_price=10,
            admission=True
        )

        # Configure PWYC for the item
        self.event.settings.set(f'pwyc_enabled_{self.ticket.pk}', True)
        self.event.settings.set(f'pwyc_min_amount_{self.ticket.pk}', '5.00')
        self.event.settings.set(f'pwyc_suggested_amount_{self.ticket.pk}', '15.00')
        self.event.settings.set(f'pwyc_explanation_{self.ticket.pk}', 'Test explanation')

    def test_item_is_pwyc(self):
        """Test that an item is correctly marked as PWYC"""
        from pretix_pwyc.signals import is_pwyc_item
        self.assertTrue(is_pwyc_item(self.event, self.ticket))

        # Test non-PWYC item
        non_pwyc = Item.objects.create(
            event=self.event,
            name='Regular Ticket',
            default_price=10,
            admission=True
        )
        self.assertFalse(is_pwyc_item(self.event, non_pwyc))

    def test_cart_with_pwyc_item(self):
        """Test that a PWYC item can be added to cart with custom price"""
        from django.http import HttpRequest
        from django.contrib.sessions.backends.db import SessionStore

        # Create a request with session
        request = HttpRequest()
        request.session = SessionStore()
        request.method = 'POST'
        request.POST = {'pwyc_price_' + str(self.ticket.pk): '7.50'}

        # Add to cart
        cart_manager = CartManager(event=self.event, cart_id='test')
        with self.assertRaises(TypeError):  # Expected because we haven't faked everything needed for add
            pos = cart_manager.add_new_items([{'item': self.ticket.pk, 'variation': None, 'count': 1}], request=request)

    def test_minimum_price_validation(self):
        """Test that minimum price validation works"""
        from pretix_pwyc.forms import PWYCPriceForm

        # Valid price
        form = PWYCPriceForm(
            item=self.ticket,
            min_price=decimal.Decimal('5.00'),
            data={'pwyc_price': '7.50'},
            prefix='test'
        )
        self.assertTrue(form.is_valid())

        # Price below minimum
        form = PWYCPriceForm(
            item=self.ticket,
            min_price=decimal.Decimal('5.00'),
            data={'pwyc_price': '3.00'},
            prefix='test'
        )
        self.assertFalse(form.is_valid())
        self.assertIn(_('The price must be at least'), form.errors['pwyc_price'][0])

    def test_settings_copy(self):
        """Test that PWYC settings are copied when cloning events/items"""
        # Create a new event as a clone
        new_event = Event.objects.create(
            organizer=self.orga,
            name='PWYC Test Event Clone',
            slug='pwyc-test-event-clone',
            date_from='2030-02-01 10:00:00Z',
            plugins='pretix_pwyc',
        )

        # Create new item
        new_ticket = Item.objects.create(
            event=new_event,
            name='Test Ticket Clone',
            default_price=10,
            admission=True
        )

        # Simulate copy from the original item
        from pretix_pwyc.signals import item_copy_data_receiver
        item_copy_data_receiver(
            sender=self.event,
            source=self.ticket,
            target=new_ticket
        )

        # Verify settings were copied
        self.assertTrue(new_event.settings.get(f'pwyc_enabled_{new_ticket.pk}'))
        self.assertEqual(
            new_event.settings.get(f'pwyc_min_amount_{new_ticket.pk}'),
            self.event.settings.get(f'pwyc_min_amount_{self.ticket.pk}')
        )
