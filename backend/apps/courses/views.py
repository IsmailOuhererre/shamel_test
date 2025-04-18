from collections import defaultdict
from venv import logger
from django.db import DatabaseError, transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.http import Http404
from .models import Course, Enrollment
from .serializers import (
    CourseSerializer, CourseCreateSerializer, 
    EnrollmentSerializer, EnrollmentCreateSerializer
)
from backend.apps.authentication.permissions import IsTeacherUser, IsStudentUser
from django.utils import timezone
from bson import ObjectId

from bson.errors import InvalidId
from django.db.models import F, Avg
from backend.apps.contracts.models import Contract
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Enrollment, Course
from backend.apps.authentication.permissions import IsTeacherUser
from bson import ObjectId
from collections import defaultdict
from rest_framework import status

from django.db import DatabaseError, transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from bson import ObjectId
from bson.errors import InvalidId
from django.db.models import F
from .models import Enrollment, Course
from .serializers import EnrollmentSerializer, EnrollmentCreateSerializer
from backend.apps.authentication.permissions import IsStudentUser
import logging

class CourseListView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Course.objects.all()
        
        # Filter by query parameters
        is_online = self.request.query_params.get('is_online')
        if is_online in ['true', 'false']:
            queryset = queryset.filter(is_online=(is_online == 'true'))
        
        is_free = self.request.query_params.get('is_free')
        if is_free in ['true', 'false']:
            queryset = queryset.filter(is_free=(is_free == 'true'))
        
        # For students only show published courses
        if hasattr(self.request.user, 'student_profile'):
            queryset = queryset.filter(status='published')
        
        return queryset

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'teacher_profile'):
            raise PermissionError("Only teachers can create courses")
        
        # Get contract from validated data if offline course
        validated_data = serializer.validated_data
        is_online = validated_data.get('is_online', True)
        contract = validated_data.get('contract') if not is_online else None
        
        # Create the course
        course = serializer.save(teacher=self.request.user)
        
        
        if is_online:
            course.status = 'published'
        else:
            if contract and contract.status == 'ready_for_enrollment':
                course.status = 'published'
            else:
                course.status = 'pending_approval'
        
        course.save()

class MyCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, 'teacher_profile'):
            return Course.objects.filter(teacher=self.request.user)
        elif hasattr(self.request.user, 'student_profile'):
            return Course.objects.filter(enrollments__student=self.request.user)
        return Course.objects.none()


class EnrollmentListView(generics.ListCreateAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    def get_serializer_class(self):
        return EnrollmentCreateSerializer if self.request.method == 'POST' else EnrollmentSerializer

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

    def post(self, request, *args, **kwargs):
        serializer = EnrollmentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        course = serializer.validated_data['course']
        user = request.user

        try:
            # Start transaction with specific isolation level
            with transaction.atomic(using='default'):
                # Check existing enrollment with lock
                if Enrollment.objects.select_for_update().filter(
                    student=user, 
                    course=course
                ).exists():
                    return Response(
                        {"detail": "Already enrolled in this course"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Validate course status with lock
                course = Course.objects.select_for_update().get(pk=course.pk)
                if course.status != 'published':
                    return Response(
                        {"detail": "Course not available for enrollment"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if course.current_students >= course.max_students:
                    return Response(
                        {"detail": "Course is full"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create enrollment
                enrollment = Enrollment.objects.create(
                    student=user,
                    course=course,
                    is_paid=course.is_free
                )

                # Update counter with explicit value to avoid F() issues
                new_count = course.current_students + 1
                Course.objects.filter(pk=course.pk).update(
                    current_students=new_count
                )

                # Verify update
                updated_course = Course.objects.get(pk=course.pk)
                if updated_course.current_students != new_count:
                    logger.error(f"Counter mismatch! Expected {new_count}, got {updated_course.current_students}")
                    raise DatabaseError("Student count update failed")

                return Response(
                    EnrollmentSerializer(enrollment).data,
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.exception("Enrollment failed")
            return Response(
                {"detail": f"Operation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EnrollmentCompleteView(generics.UpdateAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]
    lookup_field = '_id'

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

    def get_object(self):
        try:
            enrollment_id = self.kwargs.get('_id')
            
            # Try as ObjectId first
            try:
                object_id = ObjectId(enrollment_id)
                return self.get_queryset().get(_id=object_id)
            except (InvalidId, TypeError, ValueError):
                # If not valid ObjectId, try as string
                return self.get_queryset().get(_id=enrollment_id)
                
        except Enrollment.DoesNotExist:
            raise Http404(f"No enrollment found with ID {enrollment_id}")
        except Exception as e:
            raise ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        try:
            enrollment = self.get_object()
            
            if enrollment.is_completed:
                return Response(
                    {"detail": "Enrollment is already completed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            enrollment.is_completed = True
            enrollment.completion_date = timezone.now()
            enrollment.save()
            
            # student points
            if hasattr(request.user, 'student_profile'):
                request.user.student_profile.points += 10
                request.user.student_profile.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Enrollment marked as completed",
                    "data": {
                        "enrollment_id": str(enrollment._id),
                        "course_title": enrollment.course.title,
                        "completed_at": enrollment.completion_date
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Http404 as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": "Error completing enrollment",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EnrollmentRateView(generics.UpdateAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]
    lookup_field = '_id'

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

    def get_object(self):
        try:
            enrollment_id = self.kwargs.get('_id')
            
            # Try as ObjectId first
            try:
                object_id = ObjectId(enrollment_id)
                return self.get_queryset().get(_id=object_id)
            except (InvalidId, TypeError, ValueError):
                # If not valid ObjectId, try as string
                return self.get_queryset().get(_id=enrollment_id)
                
        except Enrollment.DoesNotExist:
            raise Http404(f"No enrollment found with ID {enrollment_id}")
        except Exception as e:
            raise ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        try:
            enrollment = self.get_object()
            
            # Check if enrollment belongs to the current user
            if enrollment.student != request.user:
                return Response(
                    {"status": "error", "message": "You cannot rate this enrollment"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get and validate rating
            rating = request.data.get('rating')
            try:
                # Convert to integer explicitly - this is the key fix
                rating = int(float(rating)) if isinstance(rating, str) else int(rating)
                if not 1 <= rating <= 5:
                    raise ValueError("Rating must be between 1 and 5")
            except (TypeError, ValueError) as e:
                return Response(
                    {"status": "error", "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not enrollment.is_completed:
                return Response(
                    {"status": "error", "message": "You can only rate completed courses"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update enrollment
            enrollment.rating = rating
            enrollment.review = request.data.get('review', '')
            enrollment.save()
            
            # Update course statistics with proper error handling
            try:
                course = enrollment.course
                ratings = course.enrollments.exclude(rating__isnull=True)
                course.total_ratings = ratings.count()
                
                # Safely calculate average rating
                avg_rating = ratings.aggregate(Avg('rating'))['rating__avg']
                course.rating = round(float(avg_rating), 2) if avg_rating is not None else 0
                course.save()
                
                # Update teacher points if exists
                if hasattr(course.teacher, 'teacher_profile'):
                    course.teacher.teacher_profile.points += 5
                    course.teacher.teacher_profile.save()
            except Exception as e:
                # Log the error but don't fail the request
                logger.error(f"Error updating course stats: {str(e)}")
            
            return Response(
                {
                    "status": "success",
                    "message": "Rating submitted successfully",
                    "data": {
                        "enrollment_id": str(enrollment._id),
                        "course_title": enrollment.course.title,
                        "rating": enrollment.rating,
                        "review": enrollment.review,
                        "course_avg_rating": course.rating
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Http404 as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": "Error submitting rating",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class EnrolledStudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['_id', 'full_name', 'enrollment_date', 'is_completed']
    
    def get_full_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

class TeacherStudentsListView(generics.ListAPIView):
    """
    Endpoint for teachers to view their enrolled students (full names only)
    GET params:
    - course_id: filter by specific course
    - group=course: group results by course
    """
    serializer_class = EnrolledStudentSerializer
    permission_classes = [IsAuthenticated, IsTeacherUser]

    def get_queryset(self):
        # Get enrollments for courses taught by current teacher
        return Enrollment.objects.filter(
            course__teacher=self.request.user
        ).select_related('student', 'course').order_by('-enrollment_date')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Filter by course if specified
            if course_id := request.query_params.get('course_id'):
                try:
                    queryset = queryset.filter(course___id=ObjectId(course_id))
                except:
                    return Response(
                        {"detail": "Invalid course ID format"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Group by course if requested
            if request.query_params.get('group') == 'course':
                grouped_data = defaultdict(list)
                for enrollment in queryset:
                    course_name = enrollment.course.title
                    grouped_data[course_name].append({
                        'student_id': str(enrollment.student.id),
                        'full_name': f"{enrollment.student.first_name} {enrollment.student.last_name}",
                        'enrolled_on': enrollment.enrollment_date,
                        'completed': enrollment.is_completed
                    })
                return Response(grouped_data)
            
            # Default serialized response
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"detail": f"Error retrieving student list: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )