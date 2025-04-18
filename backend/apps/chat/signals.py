from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ChatRoom, Enrollment, Contract
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=Enrollment)
def create_course_chat(sender, instance, created, **kwargs):
    if created:
        course = instance.course
        # Check if this is the first enrollment
        if course.enrollments.count() == 1:
            # Create course chat room
            teacher = course.teacher
            students = User.objects.filter(
                enrollments__course=course
            ).distinct()
            
            ChatRoom.objects.create(
                room_id=f"course_{course.id}",
                room_type='course',
                course=course,
                participants=list(students) + [teacher]
            )

@receiver(post_save, sender=Contract)
def create_school_teacher_chat(sender, instance, created, **kwargs):
    if created and instance.status == 'ready_for_enrollment':
        ChatRoom.objects.create(
            room_id=f"school_teacher_{instance.id}",
            room_type='school_teacher',
            contract=instance,
            participants=[instance.teacher, instance.school]
        )