import requests
import hmac
import hashlib
import json
from django.conf import settings
from urllib.parse import urljoin
from django.db import transaction
from decimal import Decimal

from backend.apps.payments.models import Payment

class ChargilyPaymentService:
    @staticmethod
    def create_invoice(payment):
        """Create Chargily invoice for payment with platform fee"""
        try:
            # Calculate amounts
            total_amount = float(payment.gross_amount)
            platform_fee = float(payment.platform_fee)
            recipient_amount = float(payment.net_amount)

            payload = {
                "amount": total_amount,
                "currency": "DZD",
                "payment_method": payment.payment_method,
                "client": payment.sender.email,
                "client_name": payment.sender.get_full_name(),
                "description": f"{payment.get_transaction_type_display()} Payment",
                "webhook_url": urljoin(settings.BACKEND_URL, '/api/payments/webhook/'),
                "app_fee": platform_fee,  # Explicit platform fee
                "metadata": {
                    "payment_id": str(payment.id),
                    "sender_id": str(payment.sender.id),
                    "recipient_id": str(payment.recipient.id),
                    "transaction_type": payment.transaction_type,
                    "platform_fee": str(platform_fee),
                    "contract_id": str(payment.contract.id) if payment.contract else None,
                    "course_id": str(payment.course.id) if payment.course else None
                }
            }

            # For teacher-school payments, specify the transfer
            if payment.transaction_type == 'teacher_school':
                payload['transfer_data'] = {
                    "destination": payment.recipient.chargily_account_id,
                    "amount": recipient_amount
                }

            response = requests.post(
                f"{settings.CHARGILY_CONFIG['BASE_URL']}invoices",
                headers={
                    "Authorization": f"Bearer {settings.CHARGILY_CONFIG['API_KEY']}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Chargily API Error: {str(e)}"
            if hasattr(e, 'response'):
                error_msg += f" | Response: {e.response.text}"
            raise Exception(error_msg)

    @staticmethod
    def transfer_fee_to_platform(payment_id, amount, currency='DZD'):
        """Transfer collected fee to platform wallet"""
        try:
            payload = {
                "amount": float(amount),
                "currency": currency,
                "description": f"Platform fee for payment #{payment_id}",
                "metadata": {
                    "payment_id": str(payment_id),
                    "fee_type": "platform"
                }
            }

            response = requests.post(
                f"{settings.CHARGILY_CONFIG['BASE_URL']}transfers",
                headers={
                    "Authorization": f"Bearer {settings.CHARGILY_CONFIG['API_KEY']}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Chargily Transfer Error: {str(e)}"
            if hasattr(e, 'response'):
                error_msg += f" | Response: {e.response.text}"
            raise Exception(error_msg)

    @staticmethod
    def verify_webhook(payload, signature):
        """Verify webhook signature"""
        computed_signature = hmac.new(
            settings.CHARGILY_CONFIG['WEBHOOK_SECRET'].encode(),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, computed_signature)

    @staticmethod
    def process_webhook(payload):
        """Process webhook and update payment status"""
        try:
            metadata = payload.get('metadata', {})
            payment_id = metadata.get('payment_id')
            
            if not payment_id:
                raise ValueError("Missing payment_id in webhook metadata")
            
            payment = Payment.objects.select_for_update().get(id=payment_id)
            
            if payload.get('status') == 'paid':
                payment.mark_as_completed(payload)
                return True, payment
            else:
                payment.status = 'failed'
                payment.save()
                return False, payment
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Webhook processing failed: {str(e)}")
            raise