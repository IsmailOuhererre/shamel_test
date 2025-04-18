# chat/serializers.py
from rest_framework import serializers
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Message
        fields = ['_id', 'room', 'sender', 'content', 'timestamp', 'read_by', 'is_read', 'attachments']
        read_only_fields = ['_id', 'sender', 'timestamp', 'read_by', 'is_read']

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['room_id', 'room_type', 'course', 'contract', 'participants', 
                 'created_at', 'last_activity', 'last_message', 'unread_count']
    
    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return MessageSerializer(last_message).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.exclude(read_by=request.user).count()
        return 0