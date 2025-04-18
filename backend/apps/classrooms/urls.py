from django.urls import path
from .views import (
    ClassroomView, 
    ClassroomDetailView, 
    NearbyClassroomsView
)

urlpatterns = [
    path('', ClassroomView.as_view(), name='classroom-list'),
    path('nearby/', NearbyClassroomsView.as_view(), name='nearby-classrooms'),
    path('<str:pk>/', ClassroomDetailView.as_view(), name='classroom-detail'),
]