from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
import random
from datetime import timedelta
from django.utils import timezone

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20)
    full_name = models.CharField(max_length=255)
    region_number = models.IntegerField()
    password = models.CharField(max_length=128)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'full_name', 'region_number']

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school', 'School'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
    )

    def __str__(self):
        return self.email

    def generate_verification_code(self):
        # Generate a 5-digit verification code
        code = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        expiry = timezone.now() + timedelta(minutes=15)  # Code expires in 15 minutes
        
        # Create or update verification code
        VerificationCode.objects.update_or_create(
            user=self,
            defaults={'code': code, 'expiry': expiry, 'is_used': False}
        )
        return code


class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expiry

    class Meta:
        ordering = ['-created_at']


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expiry

    class Meta:
        ordering = ['-created_at']


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    age = models.IntegerField()
    education_level = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    badges = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f"{self.user.email} - Student"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    experience_years = models.IntegerField()
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=100)
    ranking = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    badges = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'

    def __str__(self):
        return f"{self.user.email} - Teacher"


class School(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="school_profile")
    school_name = models.CharField(max_length=255)
    director_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    secondary_phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField()
    license_number = models.CharField(max_length=100)
    school_account_name = models.CharField(max_length=100)
    ranking = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    badges = models.JSONField(default=list)

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'

    def __str__(self):
        return f"{self.school_name} - School"