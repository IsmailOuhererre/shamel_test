from django.urls import path
from .views import (
    ProfileDetailView, ProfileView, ProtectedView, RegisterView, 
    LoginView, TokenRefreshView, UpdatePointsView, VerifyEmailView,
    ResendVerificationCodeView, PasswordResetRequestView, PasswordResetConfirmView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationCodeView.as_view(), name='resend-verification'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/<int:id>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('update-points/', UpdatePointsView.as_view(), name='update-points'), 
]