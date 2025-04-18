from djongo import models
from django.core.validators import MinValueValidator
from backend.apps.authentication.models import User
from backend.apps.classrooms.models import Classroom

class Contract(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('payment_pending', 'Payment Pending'),
        ('ready_for_enrollment', 'Ready for Enrollment'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ]

    _id = models.ObjectIdField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_contracts')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_contracts')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    hours_per_week = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_hours = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['school']),
            models.Index(fields=['status']),
            models.Index(fields=['classroom']),
        ]

    def __str__(self):
        return f"Contract #{self._id} - {self.classroom.name}"

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.price_per_hour * self.total_hours
        super().save(*args, **kwargs)

    @property
    def id(self):
        return str(self._id)