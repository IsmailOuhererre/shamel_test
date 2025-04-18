from django.db import models
from backend.apps.authentication.models import User

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.URLField()
    points_required = models.IntegerField()
    badge_type = models.CharField(
        max_length=20,
        choices=[
            ('student', 'Student'),
            ('teacher', 'Teacher'),
            ('school', 'School'),
            ('general', 'General')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['points_required']
        verbose_name = 'Badge'
        verbose_name_plural = 'Badges'

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges_earned')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='users_earned')
    earned_at = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']
        verbose_name = 'User Badge'
        verbose_name_plural = 'User Badges'

    def __str__(self):
        return f"{self.user.email} - {self.badge.name}"