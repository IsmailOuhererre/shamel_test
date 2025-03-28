from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token.get('user_id')
            
            if not user_id:
                logger.error("Token contains no user_id")
                raise InvalidToken("No user identifier in token")

            logger.debug(f"Looking for user ID: {user_id}")
            
            User = get_user_model()
            
            # First check if user exists using exists() for efficiency
            if not User.objects.filter(id=user_id).exists():
                logger.error(f"User ID {user_id} not found in database")
                raise AuthenticationFailed("User not found", code="user_not_found")
            
            # Get full user object with related profiles
            try:
                user = User.objects.select_related(
                    'student_profile',
                    'teacher_profile',
                    'school_profile'
                ).get(id=user_id)
                
                logger.debug(f"Successfully authenticated user: {user.id} | Email: {user.email} | Role: {user.role}")
                return user
                
            except User.DoesNotExist:
                logger.error(f"User lookup failed for ID: {user_id}")
                raise AuthenticationFailed("User not found", code="user_not_found")
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailed("Authentication failed")