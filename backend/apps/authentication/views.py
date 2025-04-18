import logging
from tokenize import TokenError
from django.db import connections
from django.db.models import F
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.db.utils import IntegrityError
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from django.db import transaction
from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer, UserProfileSerializer,
    TokenRefreshSerializer, VerifyEmailSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import TokenRefreshSerializer
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import uuid

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
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            return Response({
                'message': 'User registered successfully. Please check your email for verification code.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {"error": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        verification_code = serializer.validated_data['verification_code']

        # Mark the code as used
        verification_code.is_used = True
        verification_code.save()

        # Verify the user's email
        user.is_email_verified = True
        user.save()

        # Generate tokens after successful verification
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Email successfully verified.',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user_id': user.id
        }, status=status.HTTP_200_OK)

class ResendVerificationCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_email_verified:
            return Response(
                {"error": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate and send new verification code
        verification_code = user.generate_verification_code()
        
        # Send the email
        subject = 'Verify Your Email Address'
        context = {
            'user': user,
            'code': verification_code,
            'app_name': 'Your App Name',
        }
        
        html_message = render_to_string('email/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'New verification code sent to your email.'
        }, status=status.HTTP_200_OK)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Password reset link has been sent to your email.'
        }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Password has been reset successfully.'
        }, status=status.HTTP_200_OK)

class LoginView(APIView):
    permission_classes = [AllowAny]

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

        if not user.is_email_verified:
            return Response(
                {"error": "Email not verified. Please verify your email first."},
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

class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 1. Validate input
            serializer = TokenRefreshSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            refresh_token = serializer.validated_data['refresh']
            
            # 2. Decode token
            old_token = RefreshToken(refresh_token)
            user_id = old_token[jwt_settings.USER_ID_CLAIM]
            
            # 3. Get user from default database
            user = User.objects.using('default').get(id=user_id)
            
            # 4. Generate new tokens FIRST
            new_refresh = RefreshToken.for_user(user)
            response_data = {
                "access": str(new_refresh.access_token),
                "refresh": str(new_refresh),
            }
            
            # 5. Handle blacklist with duplicate protection
            if jwt_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    # Check if outstanding token already exists
                    outstanding_token, created = OutstandingToken.objects.using('default').get_or_create(
                        jti=old_token['jti'],
                        defaults={
                            'user': user,
                            'token': str(old_token),
                            'created_at': timezone.now(),
                            'expires_at': timezone.now() + jwt_settings.REFRESH_TOKEN_LIFETIME
                        }
                    )
                    
                    # Create blacklist entry if it doesn't exist
                    BlacklistedToken.objects.using('default').get_or_create(
                        token=outstanding_token,
                        defaults={'blacklisted_at': timezone.now()}
                    )
                    
                except IntegrityError:
                    logger.warning(f"Token {old_token['jti']} already processed")
                except Exception as e:
                    logger.error(f"Blacklist operation failed: {str(e)}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User account no longer exists"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except TokenError as e:
            return Response(
                {"error": f"Invalid token: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Refresh failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Token refresh failed"},
                status=status.HTTP_400_BAD_REQUEST
            )

class UpdatePointsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # 1. Validate points input
            try:
                points = int(request.data.get('points', 0))
                if points <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"error": "Points must be a positive integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 2. Get the authenticated user's profile
            user = request.user
            profile_attr = f"{user.role}_profile"
            
            if not hasattr(user, profile_attr):
                logger.error(f"User {user.id} missing {profile_attr}")
                return Response(
                    {"error": f"Profile not found for {user.role} role"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            profile = getattr(user, profile_attr)
            
            # 3. Atomic update to prevent race conditions
            with transaction.atomic():
                # Using F() expression for thread-safe increment
                profile.points = F('points') + points
                profile.save(update_fields=['points'])
                # Refresh to get updated value
                profile.refresh_from_db()
            
            return Response({
                "points": profile.points  # Only return the new points total
            })
            
        except Exception as e:
            logger.error(f"Failed to update points: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )