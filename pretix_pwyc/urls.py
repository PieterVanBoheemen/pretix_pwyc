from django.urls import path
from . import views

urlpatterns = [
    path('control/event/<str:organizer>/<str:event>/settings/pwyc/',
         views.PWYCSettingsView.as_view(), name='settings'),

    # AJAX endpoint for setting custom prices (no organizer/event in path for simplicity)
    path('pwyc/set-price/', views.PWYCSetPriceView.as_view(), name='set_price'),
]
