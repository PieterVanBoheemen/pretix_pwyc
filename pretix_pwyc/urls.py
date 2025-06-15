from django.urls import path
from . import views

urlpatterns = [
    path('control/event/<str:organizer>/<str:event>/settings/pwyc/',
         views.PWYCSettingsView.as_view(), name='settings'),
]
