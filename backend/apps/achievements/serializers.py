from rest_framework import serializers
from .models import Badge, UserBadge
from backend.apps.authentication.serializers import UserProfileSerializer  # Changed from UserSerializer

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['id', 'name', 'description', 'icon', 'points_required', 'badge_type']

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    user = UserProfileSerializer(read_only=True)  # Changed to UserProfileSerializer
    
    class Meta:
        model = UserBadge
        fields = ['id', 'user', 'badge', 'earned_at', 'is_seen']
        read_only_fields = ['user', 'badge', 'earned_at']