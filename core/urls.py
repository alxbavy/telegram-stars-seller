from django.urls import path

from core.views import payment_webhook

urlpatterns = [
    path('webhooks/platega/', payment_webhook, name='platega_webhook'),
]
