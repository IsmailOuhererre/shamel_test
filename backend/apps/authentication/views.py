import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.db.utils import IntegrityError
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    """Enhanced authentication with profile verification"""
    def get_user(self, validated_token):
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                logger.error("Token contains no user_id")
                raise InvalidToken("No user identifier in token")

            User = get_user_model()
            user = User.objects.select_related(
                'student_profile',
                'teacher_profile',
                'school_profile'
            ).filter(id=user_id).first()
            
            if not user:
                logger.error(f"User ID {user_id} not found in database")
                raise AuthenticationFailed("User not found", code="user_not_found")
            
            # Verify profile exists based on role
            if not self._verify_profile_exists(user):
                logger.error(f"Profile missing for user {user.id} with role {user.role}")
                raise AuthenticationFailed("Profile data missing", code="profile_missing")
                
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailed("Authentication failed")

    def _verify_profile_exists(self, user):
        """Verify the user has the appropriate profile for their role"""
        if user.role == 'student':
            return hasattr(user, 'student_profile')
        elif user.role == 'teacher':
            return hasattr(user, 'teacher_profile')
        elif user.role == 'school':
            return hasattr(user, 'school_profile')
        return True  # Skip verification if role is not specified

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'User registered successfully',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {"error": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data["user"]
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        if not user.is_active:
            return Response(
                {"error": "Account is inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

class ProfileView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ProfileDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            user = get_user_model().objects.get(id=id)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except get_user_model().DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class ProtectedView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "You have access to this protected resource!",
            "user_id": request.user.id
        }, status=status.HTTP_200_OK)