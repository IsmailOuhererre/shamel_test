# serializers.py
from rest_framework import serializers
from .models import Course, Enrollment
from backend.apps.authentication.serializers import UserProfileSerializer
from backend.apps.contracts.models import Contract
from bson import ObjectId
from django.core.exceptions import ValidationError

class CourseSerializer(serializers.ModelSerializer):
    teacher = UserProfileSerializer(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    has_access_to_attachments = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    contract = serializers.CharField(source='contract._id', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            '_id', 'title', 'description', 'teacher', 'price', 'duration_hours',
            'start_date', 'end_date', 'max_students', 'current_students',
            'is_online', 'contract', 'status', 'rating', 'total_ratings',
            'tags', 'requirements', 'syllabus', 'is_enrolled', 'is_free',
            'created_at', 'course_materials_link', 'meeting_link',
            'has_access_to_attachments', 'attachments'
        ]
        read_only_fields = [
            'teacher', 'current_students', 'rating', 'total_ratings', 'status',
            'has_access_to_attachments', 'attachments', 'contract'
        ]
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user).exists()
        return False
    
    def get_has_access_to_attachments(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        if obj.is_free:
            return True
            
        try:
            enrollment = obj.enrollments.get(student=request.user)
            return enrollment.is_paid
        except Enrollment.DoesNotExist:
            return False
    
    def get_attachments(self, obj):
        request = self.context.get('request')
        has_access = self.get_has_access_to_attachments(obj)
        
        if not has_access:
            return None
            
        return {
            'course_materials': obj.course_materials_link,
            'meeting_link': obj.meeting_link
        }

class CourseCreateSerializer(serializers.ModelSerializer):
    contract = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'price', 'duration_hours',
            'start_date', 'end_date', 'max_students', 'is_online',
            'contract', 'tags', 'requirements', 'syllabus', 'is_free',
            'course_materials_link', 'meeting_link'
        ]
    
    def validate(self, data):
        is_online = data.get('is_online', True)
        contract_id = data.get('contract')
        
        # offline course requirements
        if not is_online:
            if not contract_id:
                raise serializers.ValidationError("Contract is required for offline courses")
            
            try:
                contract = Contract.objects.get(_id=ObjectId(contract_id))
                if contract.status != 'ready_for_enrollment':
                    raise serializers.ValidationError("Contract must be in 'ready_for_enrollment' status")
                
                # Store the contract object for later use
                data['contract'] = contract
            except (Contract.DoesNotExist, TypeError, ValueError):
                raise serializers.ValidationError("Invalid contract ID or contract not found")
        
      
        if is_online:
            if contract_id:
                raise serializers.ValidationError("Contract should not be provided for online courses")
            
            
            if self.instance and self.instance.status != 'draft' or \
               (not self.instance and data.get('status', 'draft') != 'draft'):
                if not data.get('course_materials_link'):
                    raise serializers.ValidationError("Course materials link is required for online courses")
                if not data.get('meeting_link'):
                    raise serializers.ValidationError("Meeting link is required for online courses")
        
        if data.get('is_free'):
            data['price'] = 0.00
        
        return data

    def create(self, validated_data):
       # Validate that the teacher is the one creating the course
        validated_data['teacher'] = self.context['request'].user
        
        # For offline courses verifying that  teacher matches contract teacher
        if not validated_data.get('is_online', True):
            contract = validated_data.get('contract')
            if contract and contract.teacher != validated_data['teacher']:
                raise serializers.ValidationError("You can only use your own contracts")
        
        return super().create(validated_data)

class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserProfileSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    has_access_to_attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            '_id', 'student', 'course', 'enrollment_date', 'completion_date',
            'is_completed', 'progress', 'rating', 'review', 'payment_reference',
            'is_paid', 'has_access_to_attachments'
        ]
        read_only_fields = [
            'student', 'course', 'enrollment_date', 'payment_reference', 'is_paid',
            'has_access_to_attachments'
        ]
    
    def get_has_access_to_attachments(self, obj):
        return obj.has_access_to_attachments()

class EnrollmentCreateSerializer(serializers.ModelSerializer):
    course = serializers.CharField(required=True)
    
    class Meta:
        model = Enrollment
        fields = ['course']
    
    def validate(self, data):
        course_id = data.get('course')
        user = self.context['request'].user
        
        try:
            try:
                object_id = ObjectId(course_id)
                course = Course.objects.get(_id=object_id)
            except (TypeError, ValueError):
                course = Course.objects.get(_id=course_id)
                
            if course.current_students >= course.max_students:
                raise serializers.ValidationError("Course is full")
            
            if course.enrollments.filter(student=user).exists():
                raise serializers.ValidationError("You are already enrolled in this course")
            
            data['course'] = course
            return data
            
        except Course.DoesNotExist:
            raise serializers.ValidationError(f"Course with ID {course_id} does not exist")
        except Exception as e:
            raise serializers.ValidationError(f"Invalid course ID format: {str(e)}")