from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('chargily_checkout_id', 'chargily_payment_id', 'status', 'payment_url')

class CreateTeacherPaymentSerializer(serializers.Serializer):
    contract_id = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    classroom_id = serializers.CharField(required=True)
    return_url = serializers.URLField(required=True)
    back_url = serializers.URLField(required=True)