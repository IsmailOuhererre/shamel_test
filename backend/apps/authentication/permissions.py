from rest_framework.permissions import BasePermission, IsAdminUser as DRFIsAdminUser

class IsAdminUser(DRFIsAdminUser):
    """
    Allows access only to admin users.
    Inherits from DRF's built-in IsAdminUser permission.
    """
    pass

class IsTeacherUser(BasePermission):
    """
    Allows access only to users with teacher profile.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'teacher_profile')

class IsStudentUser(BasePermission):
    """
    Allows access only to users with student profile.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'student_profile')

class IsSchoolUser(BasePermission):
    """
    Allows access only to users with school profile.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'school_profile')