from django.urls import path
from .views import InitiatePaymentAPI, PaymentWebhookAPI

urlpatterns = [
    path('initiate/', InitiatePaymentAPI.as_view(), name='initiate-payment'),
    path('webhook/', PaymentWebhookAPI.as_view(), name='payment-webhook'),
]