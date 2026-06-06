from django.urls import path

from core.views import payment_webhook, test_webhook

urlpatterns = [
    path('webhooks/platega/', payment_webhook, name='platega_webhook'),
    path('webhooks/test/', test_webhook, name='test_webhook'),
]
