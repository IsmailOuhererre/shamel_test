from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, Student, Teacher, School
from rest_framework_simplejwt.tokens import RefreshToken

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

        refresh = RefreshToken.for_user(user)
        return {
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

        # Set username to email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data['email']

        # Create user with hashed password
        user = User.objects.create(
            full_name=full_name,
            role=role,
            password=make_password(password),
            **validated_data
        )

        # Create profile based on role
        if role == 'student':
            Student.objects.create(user=user, **student_data)
        elif role == 'teacher':
            Teacher.objects.create(user=user, **teacher_data)
        elif role == 'school':
            School.objects.create(user=user, **school_data)

        # Generate token for the new user
        refresh = RefreshToken.for_user(user)
        user.token = str(refresh.access_token)

        return user

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