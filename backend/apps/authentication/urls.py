from django.urls import path
from .views import ProfileDetailView, ProfileView, ProtectedView, RegisterView, LoginView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/<int:id>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('protected/', ProtectedView.as_view(), name='protected'),
]
