# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, Message
from .serializers import MessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user = self.scope['user']
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Verify user has access to the room
        if not await self.verify_room_access():
            await self.close()
            return
        
        self.room_group_name = f'chat_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def verify_room_access(self):
        return ChatRoom.objects.filter(
            room_id=self.room_id,
            participants=self.user
        ).exists()
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'chat_message':
            content = text_data_json['content']
            
            # Save message to database
            message = await self.save_message(content)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data
                }
            )
        elif message_type == 'typing':
            # Broadcast typing notification
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_notification',
                    'user_id': str(self.user.id),
                    'is_typing': text_data_json['is_typing']
                }
            )
    
    @database_sync_to_async
    def save_message(self, content):
        room = ChatRoom.objects.get(room_id=self.room_id)
        message = Message.objects.create(
            room=room,
            sender=self.user,
            content=content
        )
        message.read_by.add(self.user)
        room.save()  # Update last activity
        return message
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_notification(self, event):
        # Send typing notification to WebSocket
        if str(self.user.id) != event['user_id']:  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing']
            }))