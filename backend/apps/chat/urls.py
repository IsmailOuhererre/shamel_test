# chat/urls.py
from django.urls import path
from .views import (
    ChatRoomListView,
    CourseChatDetailView,
    SchoolTeacherChatDetailView,
    MessageListView,
    SendMessageView,
    MarkMessagesAsReadView
)

urlpatterns = [
    path('rooms/', ChatRoomListView.as_view(), name='chat-room-list'),
    path('rooms/course/<uuid:course_id>/', CourseChatDetailView.as_view(), name='course-chat-detail'),
    path('rooms/contract/<uuid:contract_id>/', SchoolTeacherChatDetailView.as_view(), name='school-teacher-chat-detail'),
    path('rooms/<str:room_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('rooms/<str:room_id>/send/', SendMessageView.as_view(), name='send-message'),
    path('rooms/<str:room_id>/mark-read/', MarkMessagesAsReadView.as_view(), name='mark-messages-read'),
]