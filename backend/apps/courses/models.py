# models.py
from djongo import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from backend.apps.authentication.models import User
from backend.apps.contracts.models import Contract

class Course(models.Model):
    _id = models.ObjectIdField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_hours = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_students = models.IntegerField()
    current_students = models.IntegerField(default=0)
    is_online = models.BooleanField(default=True)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('pending_approval', 'Pending Approval'),
            ('published', 'Published'),
            ('in_process', 'In Process'),
            ('ready', 'Ready'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='draft'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_ratings = models.IntegerField(default=0)
    tags = models.JSONField(default=list)
    requirements = models.JSONField(default=list)
    syllabus = models.JSONField(default=list)
    is_free = models.BooleanField(default=False)
    course_materials_link = models.URLField(max_length=512, blank=True, null=True)
    meeting_link = models.URLField(max_length=512, blank=True, null=True)

    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['teacher']),
            models.Index(fields=['is_online']),
            models.Index(fields=['status']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_free']),
            models.Index(fields=['contract']),
        ]

    def __str__(self):
        return f"{self.title} by {self.teacher.email}"

    def clean(self):
       
        if self.is_online and self.status in ['published', 'in_process']:
            if not self.course_materials_link:
                raise ValidationError("Course materials link is required for online courses")
            if not self.meeting_link:
                raise ValidationError("Meeting link is required for online courses")
        
        
        if not self.is_online:
            if not self.contract:
                raise ValidationError("Contract is required for offline courses")
            if self.contract.status != 'ready_for_enrollment':
                raise ValidationError("Contract must be in 'ready_for_enrollment' status")
            if self.contract.teacher != self.teacher:
                raise ValidationError("Contract teacher must match course teacher")

class Enrollment(models.Model):
    _id = models.ObjectIdField()
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    progress = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    review = models.TextField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        db_table = 'enrollments'
        unique_together = ('student', 'course')
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['course']),
            models.Index(fields=['is_completed']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        return f"{self.student.email} enrolled in {self.course.title}"

    def has_access_to_attachments(self):
        """Check if student has access to course attachments"""
        return self.course.is_free or self.is_paid