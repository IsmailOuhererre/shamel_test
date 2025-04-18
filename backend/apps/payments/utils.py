import requests
from django.conf import settings
from .models import Payment
from datetime import datetime, timedelta

def create_chargily_payment(user, payment_data):
    """
    Create a payment invoice via Chargily API
    

    """
    payload = {
        'client': user.email,
        'client_name': user.full_name,
        'invoice_number': f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'amount': float(payment_data['amount']),
        'discount': 0,
        'back_url': settings.FRONTEND_URL + '/payment/callback',
        'webhook_url': settings.BACKEND_URL + '/api/payments/chargily/webhook/',
        'mode': 'CIB',  # or 'EDAHABIA'
        'comment': payment_data['description'],
        'metadata': payment_data.get('metadata', {})
    }
    
    headers = {
        'X-Authorization': settings.CHARGILY_API_KEY,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        settings.CHARGILY_BASE_URL,
        json=payload,
        headers=headers
    )
    
    if response.status_code != 201:
        raise Exception(f"Chargily API error: {response.text}")
    
    data = response.json()
    
    # Create payment record
    payment = Payment.objects.create(
        user=user,
        payment_type=payment_data['payment_type'],
        amount=payment_data['amount'],
        currency=payment_data.get('currency', 'DZD'),
        description=payment_data['description'],
        status='pending',
        chargily_id=data['id'],
        chargily_url=data['checkout_url'],
        invoice_number=data['invoice_number'],
        metadata=payment_data.get('metadata', {})
    )
    
    return payment

def check_chargily_payment_status(payment):
    """
    Check the status of a payment via Chargily API
    """
    if payment.status in ['paid', 'failed', 'refunded']:
        return payment
    
    headers = {
        'X-Authorization': settings.CHARGILY_API_KEY,
        'Accept': 'application/json'
    }
    
    response = requests.get(
        f"{settings.CHARGILY_BASE_URL}/{payment.chargily_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        return payment
    
    data = response.json()
    
    if data['status'] == 'paid' and payment.status != 'paid':
        payment.status = 'paid'
        payment.paid_at = datetime.now()
        payment.save()
        
        # Trigger payment completed signal
        from .signals import payment_completed
        payment_completed.send(sender=payment.__class__, instance=payment)
    
    elif data['status'] == 'failed' and payment.status != 'failed':
        payment.status = 'failed'
        payment.save()
    
    return payment