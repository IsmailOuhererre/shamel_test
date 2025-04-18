from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BadgeViewSet, UserBadgeViewSet, AdminBadgeViewSet

router = DefaultRouter()
router.register(r'badges', BadgeViewSet, basename='badge')
router.register(r'user-badges', UserBadgeViewSet, basename='user-badge')

admin_router = DefaultRouter()
admin_router.register(r'admin/badges', AdminBadgeViewSet, basename='admin-badge')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(admin_router.urls)),
]