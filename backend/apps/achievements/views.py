from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Badge, UserBadge
from .serializers import BadgeSerializer, UserBadgeSerializer
from backend.apps.authentication.permissions import IsAdminUser

class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by badge type if provided
        badge_type = self.request.query_params.get('type', None)
        if badge_type:
            queryset = queryset.filter(badge_type=badge_type)
        
        return queryset

class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserBadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_seen(self, request, pk=None):
        user_badge = self.get_object()
        
        if user_badge.user != request.user:
            return Response({"detail": "You can only mark your own badges as seen"}, status=403)
        
        if not user_badge.is_seen:
            user_badge.is_seen = True
            user_badge.save()
        
        return Response({"status": "Badge marked as seen"})

class AdminBadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def award(self, request, pk=None):
        badge = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({"detail": "user_id is required"}, status=400)
        
        # Check if user already has this badge
        if UserBadge.objects.filter(user_id=user_id, badge=badge).exists():
            return Response({"detail": "User already has this badge"}, status=400)
        
        user_badge = UserBadge.objects.create(
            user_id=user_id,
            badge=badge
        )
        
        # TODO: Send notification to user
        
        return Response(UserBadgeSerializer(user_badge).data)