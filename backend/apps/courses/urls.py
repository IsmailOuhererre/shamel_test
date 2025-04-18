# backend/apps/courses/urls.py
from django.urls import path

from backend.apps.courses.models import Course, Enrollment
from .views import (
    CourseListView, MyCoursesView, EnrollmentListView,
    EnrollmentCompleteView, EnrollmentRateView, TeacherStudentsListView
)

urlpatterns = [
    path('', CourseListView.as_view(), name='course-list'),
    path('my-courses/', MyCoursesView.as_view(), name='my-courses'),
    
    path('enrollments/', EnrollmentListView.as_view(), name='enrollment-list'),
    path('enrollments/<str:_id>/complete/', EnrollmentCompleteView.as_view(), name='enrollment-complete'),
    path('enrollments/<str:_id>/rate/', EnrollmentRateView.as_view(), name='enrollment-rate'),
    path('teacher/students/', TeacherStudentsListView.as_view(), name='teacher-students'),
]# Add this temporary debug route to your urls.py:

