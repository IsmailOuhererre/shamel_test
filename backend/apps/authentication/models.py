from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20)
    full_name = models.CharField(max_length=255)
    region_number = models.IntegerField()
    password = models.CharField(max_length=128)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'full_name', 'region_number']

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school', 'School'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # Fix for Django auth conflicts
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


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    age = models.IntegerField()
    education_level = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    badges = models.JSONField(default=list)  # Stores badge IDs/icons as [{"id": 1, "name": "Top Learner", "icon": "url"}]

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