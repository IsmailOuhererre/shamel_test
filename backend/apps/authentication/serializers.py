from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, Student, Teacher, School, VerificationCode, PasswordResetToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import uuid
from datetime import timedelta
from django.utils import timezone

# Email styling configuration
VERIFICATION_EMAIL_STYLES = {
    'body': 'font-family: Arial, sans-serif; background-color: #f5f5f5; color: #333333; margin: 0; padding: 0;',
    'container': 'max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border: 1px solid #dddddd; border-radius: 8px;',
    'header': 'text-align: center; padding: 20px 0; border-bottom: 1px solid #FFD92F;',
    'header_h1': 'color: #FFD92F; font-size: 28px; margin: 0;',
    'content': 'padding: 20px 0; color: #333333;',
    'verification_code': 'background-color: #f8f8f8; color: #FFD92F; font-size: 24px; font-weight: bold; text-align: center; padding: 15px; margin: 20px 0; border-radius: 4px; letter-spacing: 3px; border: 1px dashed #FFD92F;',
    'footer': 'text-align: center; padding-top: 20px; border-top: 1px solid #eeeeee; font-size: 12px; color: #999999;'
}

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Incorrect password."})

        if not user.is_email_verified:
            raise serializers.ValidationError({"email": "Email not verified. Please verify your email first."})

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "token": str(refresh.access_token),
        }

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=True)
    
    # Student fields
    age = serializers.IntegerField(required=False)
    education_level = serializers.CharField(required=False)
    specialization = serializers.CharField(required=False)
    
    # Teacher fields
    experience_years = serializers.IntegerField(required=False)
    qualification = serializers.CharField(required=False)
    
    # School fields
    school_name = serializers.CharField(required=False)
    director_name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    secondary_phone_number = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False)
    license_number = serializers.CharField(required=False)
    school_account_name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'full_name', 'username', 'email', 'password',
            'role', 'phone', 'region_number',
            # Student fields
            'age', 'education_level', 'specialization',
            # Teacher fields
            'experience_years', 'qualification',
            # School fields
            'school_name', 'director_name', 'phone_number', 'secondary_phone_number',
            'address', 'license_number', 'school_account_name'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'full_name': {'required': True},
        }

    def validate(self, data):
        if not data.get('full_name'):
            raise serializers.ValidationError({"full_name": "This field is required."})

        role = data.get('role')

        if role == 'student':
            required_fields = ['age', 'education_level', 'specialization']
            if not all(field in data for field in required_fields):
                raise serializers.ValidationError({
                    "detail": "Students must provide age, education level, and specialization."
                })

        elif role == 'teacher':
            required_fields = ['experience_years', 'qualification']
            if not all(field in data for field in required_fields):
                raise serializers.ValidationError({
                    "detail": "Teachers must provide experience years and qualification."
                })

        elif role == 'school':
            required_fields = [
                'school_name', 'director_name', 'phone_number',
                'address', 'license_number', 'school_account_name'
            ]
            if not all(field in data for field in required_fields):
                raise serializers.ValidationError({
                    "detail": "Schools must provide name, director, phone, address, license, and account name."
                })

        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        role = validated_data.pop('role')
        full_name = validated_data.pop('full_name')
        
        # Extract profile-specific data
        student_data = {}
        teacher_data = {}
        school_data = {}

        if role == 'student':
            student_fields = ['age', 'education_level', 'specialization']
            for field in student_fields:
                if field in validated_data:
                    student_data[field] = validated_data.pop(field)
            student_data.update({
                'points': 0,
                'badges': []
            })
        
        elif role == 'teacher':
            teacher_fields = ['experience_years', 'qualification']
            for field in teacher_fields:
                if field in validated_data:
                    teacher_data[field] = validated_data.pop(field)
            teacher_data.update({
                'points': 0,
                'badges': []
            })
        
        elif role == 'school':
            school_fields = [
                'school_name', 'director_name', 'phone_number',
                'secondary_phone_number', 'address', 'license_number',
                'school_account_name'
            ]
            for field in school_fields:
                if field in validated_data:
                    school_data[field] = validated_data.pop(field)
            school_data.update({
                'points': 0,
                'badges': []
            })

        if not validated_data.get('username'):
            validated_data['username'] = validated_data['email']

        # Create user with hashed password
        user = User.objects.create(
            full_name=full_name,
            role=role,
            password=make_password(password),
            is_email_verified=False,
            **validated_data
        )

        if role == 'student':
            Student.objects.create(user=user, **student_data)
        elif role == 'teacher':
            Teacher.objects.create(user=user, **teacher_data)
        elif role == 'school':
            School.objects.create(user=user, **school_data)

        # Generate and send verification code
        verification_code = user.generate_verification_code()
        self.send_verification_email(user, verification_code)

        return user

    def send_verification_email(self, user, code):
        subject = 'Verify Your Email Address'
        context = {
            'user': user,
            'code': code,
            'app_name': settings.APP_NAME,
            'styles': VERIFICATION_EMAIL_STYLES
        }
        
        html_message = render_to_string('email/verification_email.html', context)
        plain_message = f"""Verify Your Email Address

Hello {user.full_name},
Thank you for registering with {settings.APP_NAME}. To complete your registration, please enter the following verification code in the app:

Verification Code: {code}

This code will expire in 15 minutes. If you didn't request this, please ignore this email.

© {settings.APP_NAME} {timezone.now().year}. All rights reserved.
"""
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=5)

    def validate(self, data):
        email = data.get('email')
        code = data.get('code')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'User with this email does not exist.'})

        verification_code = VerificationCode.objects.filter(
            user=user,
            code=code,
            is_used=False
        ).order_by('-created_at').first()

        if not verification_code or not verification_code.is_valid():
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})

        data['user'] = user
        data['verification_code'] = verification_code
        return data

    def save(self):
        user = self.validated_data['user']
        verification_code = self.validated_data['verification_code']

        # Mark the code as used
        verification_code.is_used = True
        verification_code.save()

        # Verify the user's email
        user.is_email_verified = True
        user.save()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return user

    def save(self):
        user = self.validated_data['email']
        token = str(uuid.uuid4())
        expiry = timezone.now() + timedelta(hours=1)
        
        PasswordResetToken.objects.update_or_create(
            user=user,
            defaults={'token': token, 'expiry': expiry, 'is_used': False}
        )
        
        self.send_password_reset_email(user, token)

    def send_password_reset_email(self, user, token):
        subject = 'Password Reset Request'
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'app_name': settings.APP_NAME,
            'styles': VERIFICATION_EMAIL_STYLES
        }
        
        html_message = render_to_string('email/password_reset_email.html', context)
        plain_message = f"""Password Reset Request

Hello {user.full_name},
We received a request to reset your password for your {settings.APP_NAME} account.

Click this link to reset your password: {reset_url}

If you didn't request this, please ignore this email. The link will expire in 1 hour.

© {settings.APP_NAME} {timezone.now().year}. All rights reserved.
"""
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

        try:
            reset_token = PasswordResetToken.objects.get(
                token=token,
                is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid or expired token.'})

        if not reset_token.is_valid():
            raise serializers.ValidationError({'token': 'Invalid or expired token.'})

        data['reset_token'] = reset_token
        return data

    def save(self):
        reset_token = self.validated_data['reset_token']
        new_password = self.validated_data['new_password']

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.is_used = True
        reset_token.save()

class UserProfileSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name', 'role', 
            'phone', 'region_number', 'profile', 'points', 'badges'
        ]

    def get_profile(self, obj):
        if obj.role == 'student' and hasattr(obj, 'student_profile'):
            return {
                "age": obj.student_profile.age,
                "education_level": obj.student_profile.education_level,
                "specialization": obj.student_profile.specialization,
            }
        elif obj.role == 'teacher' and hasattr(obj, 'teacher_profile'):
            return {
                "experience_years": obj.teacher_profile.experience_years,
                "qualification": obj.teacher_profile.qualification,
                "specialization": obj.teacher_profile.specialization,
                "ranking": obj.teacher_profile.ranking,
            }
        elif obj.role == 'school' and hasattr(obj, 'school_profile'):
            profile_data = {
                "school_name": obj.school_profile.school_name,
                "director_name": obj.school_profile.director_name,
                "phone_number": obj.school_profile.phone_number,
                "address": obj.school_profile.address,
                "license_number": obj.school_profile.license_number,
                "school_account_name": obj.school_profile.school_account_name,
                "ranking": obj.school_profile.ranking,
            }
            if obj.school_profile.secondary_phone_number:
                profile_data["secondary_phone_number"] = obj.school_profile.secondary_phone_number
            return profile_data
        return None

    def get_points(self, obj):
        if obj.role == 'student' and hasattr(obj, 'student_profile'):
            return obj.student_profile.points
        elif obj.role == 'teacher' and hasattr(obj, 'teacher_profile'):
            return obj.teacher_profile.points
        elif obj.role == 'school' and hasattr(obj, 'school_profile'):
            return obj.school_profile.points
        return 0

    def get_badges(self, obj):
        if obj.role == 'student' and hasattr(obj, 'student_profile'):
            return obj.student_profile.badges
        elif obj.role == 'teacher' and hasattr(obj, 'teacher_profile'):
            return obj.teacher_profile.badges
        elif obj.role == 'school' and hasattr(obj, 'school_profile'):
            return obj.school_profile.badges
        return []

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class UpdatePointsSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=1)
    
    def validate_points(self, value):
        if value <= 0:
            raise serializers.ValidationError("Points must be positive")
        return value