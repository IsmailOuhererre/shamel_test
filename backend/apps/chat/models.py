# chat/models.py
from djongo import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

User = get_user_model()

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('course', 'Course Chat'),
        ('school_teacher', 'School-Teacher Chat'),
        ('private', 'Private Chat'),
    ]
    
    room_id = models.CharField(max_length=100, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    course = models.ForeignKey('courses.Course', null=True, blank=True, on_delete=models.CASCADE)
    contract = models.ForeignKey('contracts.Contract', null=True, blank=True, on_delete=models.CASCADE)
    participants = models.ArrayReferenceField(
        to=User,
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_chatroom' 
        indexes = [
            models.Index(fields=['room_id']),
            models.Index(fields=['room_type']),
            models.Index(fields=['course']),
            models.Index(fields=['contract']),
            models.Index(fields=['last_activity']),
            models.Index(fields=['participants']),
        ]
        ordering = ['-last_activity']
    
    def __str__(self):
        if self.room_type == 'course':
            return f"Course Chat: {self.course.title}"
        elif self.room_type == 'school_teacher':
            return f"School-Teacher Chat: {self.contract}"
        return f"Private Chat: {self.room_id}"
    
    def add_participant(self, user):
        """Add a participant to the chat room"""
        if user not in self.participants.all():
            self.participants.add(user)
            self.save()
    
    def remove_participant(self, user):
        """Remove a participant from the chat room"""
        if user in self.participants.all():
            self.participants.remove(user)
            self.save()

class Attachment(models.Model):
    url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

class Message(models.Model):
    _id = models.ObjectIdField()
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ArrayReferenceField(
        to=User,
        on_delete=models.CASCADE,
        related_name='read_messages'
    )
    attachments = models.ArrayReferenceField(
        to=Attachment,
        on_delete=models.CASCADE,
        related_name='messages',
        blank=True,
        null=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['room', '-timestamp']),
            models.Index(fields=['sender']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['read_by']),
        ]
        ordering = ['-timestamp']
    
    def mark_as_read(self, user):
        """Mark message as read by a user"""
        if user not in self.read_by.all():
            self.read_by.add(user)
            self.save()
    
    @property
    def is_read(self):
        """Check if message has been read by all participants"""
        return self.read_by.count() == self.room.participants.count()

@receiver(post_save, sender='contracts.Contract')
def handle_contract_update(sender, instance, created, **kwargs):
    """
    Handle contract updates to manage school-teacher chat rooms
    """
    if instance.status == 'ready_for_enrollment':
        # Create or update school-teacher chat room
        room_id = f"school_teacher_{instance.id}"
        with transaction.atomic():
            room, created = ChatRoom.objects.get_or_create(
                room_id=room_id,
                defaults={
                    'room_type': 'school_teacher',
                    'contract': instance,
                }
            )
            # Ensure both school and teacher are participants
            room.add_participant(instance.teacher)
            room.add_participant(instance.school)
    
    elif instance.status in ['rejected', 'cancelled', 'completed']:
        # Optionally archive or disable the chat room
        pass

@receiver(post_save, sender='courses.Enrollment')
def handle_enrollment_update(sender, instance, created, **kwargs):
    """
    Handle enrollment updates to manage course chat rooms
    """
    if created:
        course = instance.course
        room_id = f"course_{course.id}"
        
        with transaction.atomic():
            room, created = ChatRoom.objects.get_or_create(
                room_id=room_id,
                defaults={
                    'room_type': 'course',
                    'course': course,
                }
            )
            # Add teacher if not already present
            if course.teacher not in room.participants.all():
                room.add_participant(course.teacher)
            
            # Add student
            room.add_participant(instance.student)
    
    elif instance.is_completed:
        # Optionally remove student from chat or mark as read-only
        pass