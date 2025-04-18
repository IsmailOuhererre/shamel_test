from djongo import models
from django.conf import settings
from django.utils import timezone
from bson import ObjectId
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Leaderboard(models.Model):
    _id = models.ObjectIdField(primary_key=True, default=ObjectId)
    user_id = models.CharField(max_length=24, db_index=True, unique=True)
    user_name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher'), 
        ('school', 'School')
    ], db_index=True)
    points = models.IntegerField(default=0, db_index=True, validators=[MinValueValidator(0)])
    rank = models.IntegerField(default=0, db_index=True, validators=[MinValueValidator(1)])
    badges = models.JSONField(default=list)
    profile_sync_version = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboard'
        indexes = [
            models.Index(fields=['role', 'rank']),
            models.Index(fields=['role', '-points']),
            models.Index(fields=['user_id', 'role'], name='user_role_idx'),
        ]
        ordering = ['role', 'rank']

    def __str__(self):
        return f"{self.user_name} ({self.role}): {self.points} pts (#{self.rank})"

    def save(self, *args, **kwargs):
        self.points = max(0, self.points)
        self.rank = max(1, self.rank)
        super().save(*args, **kwargs)

class Badge(models.Model):
    _id = models.ObjectIdField(primary_key=True, default=ObjectId)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500)
    icon_url = models.URLField(max_length=512)
    points_required = models.IntegerField(null=True, blank=True, db_index=True, 
                                       validators=[MinValueValidator(0)])
    role_specific = models.CharField(max_length=10, null=True, blank=True, choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school', 'School')
    ])
    rank_required = models.IntegerField(null=True, blank=True, db_index=True,
                                      validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'badges'
        ordering = ['points_required']
        verbose_name_plural = 'Badges'

    def __str__(self):
        return f"{self.name} (Points: {self.points_required or 'N/A'})"

    def clean(self):
        if self.points_required is None and self.rank_required is None:
            raise ValidationError("Either points_required or rank_required must be set")