from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from decimal import Decimal
import json
from datetime import datetime
from .models import Payment

class InitiatePaymentAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            transaction_type = data.get('transaction_type')
            
           
            if transaction_type not in ['student_teacher', 'teacher_school']:
                return Response(
                    {'error': 'Invalid transaction type'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

           
            required_fields = ['recipient_id', 'amount', 'payment_method']
            if transaction_type == 'student_teacher':
                required_fields.append('course_id')
            else:
                required_fields.append('contract_id')

            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'Missing required field: {field}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

           
            try:
                amount = Decimal(str(data['amount']))
                if amount <= 0:
                    return Response(
                        {'error': 'Amount must be greater than 0'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except:
                return Response(
                    {'error': 'Invalid amount format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get recipient
            from django.contrib.auth import get_user_model
            recipient = get_user_model().objects.get(id=data['recipient_id'])

            with transaction.atomic():
               
                payment = Payment(
                    sender=request.user,
                    recipient=recipient,
                    gross_amount=amount,
                    transaction_type=transaction_type,
                    payment_method=data['payment_method'],
                    metadata=data
                )
                
                # Set relationship
                if transaction_type == 'student_teacher':
                    from courses.models import Course
                    payment.course = Course.objects.get(id=data['course_id'])
                else:
                    from contracts.models import Contract
                    payment.contract = Contract.objects.get(
                        id=data['contract_id'],
                        teacher=request.user  # Ensure teacher owns contract
                    )
                
              
                payment.initiate_payment()
                
                # Create Chargily invoice with platform fee
                from .services import ChargilyPaymentService
                invoice = ChargilyPaymentService.create_invoice(payment)
                
                # Update payment with Chargily details
                payment.chargily_id = invoice['id']
                payment.invoice_number = invoice['invoice_number']
                payment.save()

                return Response({
                    'payment_id': payment.id,
                    'invoice_number': payment.invoice_number,
                    'checkout_url': invoice['checkout_url'],
                    'gross_amount': str(payment.gross_amount),
                    'platform_fee': str(payment.platform_fee),
                    'net_amount': str(payment.net_amount),
                    'status': payment.status
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentWebhookAPI(APIView):
    def post(self, request):
        try:
            # Verify signature
            from .services import ChargilyPaymentService
            signature = request.headers.get('X-Signature-256')
            if not signature:
                return Response({'error': 'Missing signature'}, status=status.HTTP_401_UNAUTHORIZED)
                
            if not ChargilyPaymentService.verify_webhook(request.body, signature):
                return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Process webhook
            data = json.loads(request.body)
            success, payment = ChargilyPaymentService.process_webhook(data)
            
            if success:
                # Trigger async notifications
                from payments.tasks import send_payment_success_notifications
                send_payment_success_notifications.delay(payment.id)
                
                return Response({'status': 'success'})
            else:
                return Response({'status': 'failed'})
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )