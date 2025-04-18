# chat/views.py
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from django.db.models import Q
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ChatRoomListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(participants=user).order_by('-last_activity')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class CourseChatDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get course chat room with messages"""
        try:
            room = ChatRoom.objects.get(
                room_type='course',
                course_id=course_id,
                participants=request.user
            )
            
            serializer = ChatRoomSerializer(room, context={'request': request})
            return Response(serializer.data)
        
        except ChatRoom.DoesNotExist:
            return Response(
                {"error": "Chat room not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )

class SchoolTeacherChatDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contract_id):
        """Get school-teacher chat room with messages"""
        try:
            room = ChatRoom.objects.get(
                room_type='school_teacher',
                contract_id=contract_id,
                participants=request.user
            )
            
            serializer = ChatRoomSerializer(room, context={'request': request})
            return Response(serializer.data)
        
        except ChatRoom.DoesNotExist:
            return Response(
                {"error": "Chat room not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )

class MessageListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(
            ChatRoom,
            room_id=room_id,
            participants=self.request.user
        )
        return Message.objects.filter(room=room).order_by('-timestamp')
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Mark messages as read when fetched
        room_id = self.kwargs['room_id']
        room = get_object_or_404(
            ChatRoom,
            room_id=room_id,
            participants=self.request.user
        )
        unread_messages = Message.objects.filter(
            room=room
        ).exclude(read_by=self.request.user)
        
        for message in unread_messages:
            message.mark_as_read(self.request.user)
        
        return response

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, room_id):
        """Send message to a chat room"""
        room = get_object_or_404(
            ChatRoom,
            room_id=room_id,
            participants=request.user
        )
        
        serializer = MessageSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save(
                room=room,
                sender=request.user
            )
            message.mark_as_read(request.user)  # Mark as read by sender
            
            # Update last activity
            room.save()
            
            # Send real-time update (implementation depends on your real-time solution)
            self._send_realtime_update(room_id, message)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_realtime_update(self, room_id, message):
        """Implement with your preferred real-time solution (e.g., WebSockets, Firebase)"""
        pass

class MarkMessagesAsReadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, room_id):
        """Mark all messages in a room as read for the current user"""
        room = get_object_or_404(
            ChatRoom,
            room_id=room_id,
            participants=request.user
        )
        
        unread_messages = Message.objects.filter(
            room=room
        ).exclude(read_by=request.user)
        
        for message in unread_messages:
            message.mark_as_read(request.user)
        
        return Response(
            {"status": f"Marked {unread_messages.count()} messages as read"},
            status=status.HTTP_200_OK
        )