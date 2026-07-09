from django.urls import path

from core.views import payment_webhook, fragment_webhook, test_webhook
from core.integrations.fragment.client import FRAGMENT_WEBHOOK
from core.integrations.platega.client import PLATEGA_WEBHOOK


urlpatterns = [
    path("webhooks/platega/", payment_webhook, name=PLATEGA_WEBHOOK),
    path("webhooks/fragment/", fragment_webhook, name=FRAGMENT_WEBHOOK),
    path("webhooks/test/", test_webhook, name="test_webhook"),
]
