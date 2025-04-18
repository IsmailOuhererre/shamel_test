from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

class LeaderboardView(APIView):
    def get(self, request):
        """
        Get leaderboard data with fast cached response
        """
        try:
            from .utils import get_cached_leaderboard
            leaderboard_data = get_cached_leaderboard()
            return Response(leaderboard_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Leaderboard fetch failed: {str(e)}")
            return Response(
                {"error": "Could not retrieve leaderboard"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserLeaderboardStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's status with real-time profile sync"""
        try:
            from .utils import get_user_leaderboard_status
            
            user = request.user
            role = None
            
            if hasattr(user, 'student_profile'):
                role = 'student'
                profile = user.student_profile
            elif hasattr(user, 'teacher_profile'):
                role = 'teacher'
                profile = user.teacher_profile
            elif hasattr(user, 'school_profile'):
                role = 'school'
                profile = user.school_profile
            
            if not role:
                return Response(
                    {"error": "User has no associated profile"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get status from leaderboard
            user_status = get_user_leaderboard_status(user, role)
            
            if user_status:
                return Response(user_status, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "message": "You need to gain more points to appear on the leaderboard", 
                        "is_on_leaderboard": False,
                        "user_id": str(user.id),
                        "user_name": user.get_full_name() or user.username,
                        "role": role,
                        "points": getattr(profile, 'points', 0)
                    },
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"User status fetch failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Could not check your leaderboard status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )