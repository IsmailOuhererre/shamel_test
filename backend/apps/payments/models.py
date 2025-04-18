from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import transaction

class Payment(models.Model):
    TRANSACTION_TYPES = [
        ('student_teacher', 'Student to Teacher'),
        ('teacher_school', 'Teacher to School')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

    # Core relationships
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_payments',
        on_delete=models.PROTECT
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_payments',
        on_delete=models.PROTECT
    )
    
    # Financial details
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee_transferred = models.BooleanField(default=False)
    
    # Transaction metadata
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    payment_method = models.CharField(max_length=20, default='EDAHABIA')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    chargily_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    fee_transfer_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Relationships
    contract = models.ForeignKey(
        'contracts.Contract',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    course = models.ForeignKey(
        'courses.Course',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    fee_transferred_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['recipient']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['platform_fee_transferred']),
        ]

    def __str__(self):
        return f"Payment #{self.id}: {self.sender} → {self.recipient} ({self.gross_amount} DZD)"

    def calculate_fees(self):
        """Calculate 5% platform fee and net amount"""
        self.platform_fee = (self.gross_amount * Decimal('0.05')).quantize(Decimal('0.01'))
        self.net_amount = self.gross_amount - self.platform_fee
        return self.platform_fee, self.net_amount

    def initiate_payment(self):
        """Prepare payment with calculated fees"""
        self.calculate_fees()
        self.save()
        return self

    def mark_as_completed(self, chargily_data):
        """Handle successful payment completion"""
        with transaction.atomic():
            # Update payment status
            self.status = 'completed'
            self.chargily_id = chargily_data.get('id')
            self.invoice_number = chargily_data.get('invoice_number')
            self.completed_at = timezone.now()
            self.save()

            # Record platform fee
            PlatformFee.objects.create(
                payment=self,
                amount=self.platform_fee
            )

            # Update related objects
            if self.transaction_type == 'teacher_school' and self.contract:
                self._update_contract_status()
            elif self.transaction_type == 'student_teacher' and self.course:
                self._create_enrollment()

            # Update wallets
            self._update_wallet_balances()

            # Transfer fee to platform wallet
            self._transfer_platform_fee()

            return self

    def _transfer_platform_fee(self):
        """Transfer platform fee to Chargily wallet"""
        from .services import ChargilyPaymentService
        
        if self.platform_fee <= 0 or self.platform_fee_transferred:
            return
            
        try:
            transfer_data = ChargilyPaymentService.transfer_fee_to_platform(
                payment_id=self.id,
                amount=self.platform_fee,
                currency='DZD'
            )
            
            self.fee_transfer_id = transfer_data.get('id')
            self.platform_fee_transferred = True
            self.fee_transferred_at = timezone.now()
            self.save()
            
        except Exception as e:
            # Log error but don't fail the payment
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to transfer platform fee for payment {self.id}: {str(e)}")

    def _update_contract_status(self):
        """Update contract after teacher-school payment"""
        self.contract.status = 'ready_for_enrollment'
        self.contract.payment_reference = self.invoice_number
        self.contract.save()

    def _create_enrollment(self):
        """Create enrollment after student-teacher payment"""
        from courses.models import Enrollment
        Enrollment.objects.create(
            student=self.sender,
            course=self.course,
            is_paid=True,
            payment_reference=self.invoice_number
        )

    def _update_wallet_balances(self):
        """Update wallet balances for all parties"""
        from wallets.models import Wallet
        
        # Deduct from sender
        Wallet.objects.filter(user=self.sender).update(
            balance=models.F('balance') - self.gross_amount
        )
        
        # Add to recipient
        Wallet.objects.filter(user=self.recipient).update(
            balance=models.F('balance') + self.net_amount
        )

class PlatformFee(models.Model):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='fee_record'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transferred = models.BooleanField(default=False)
    transfer_id = models.CharField(max_length=100, blank=True, null=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    transferred_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Platform Fees"

    def __str__(self):
        return f"Platform Fee: {self.amount} DZD from Payment #{self.payment_id}"