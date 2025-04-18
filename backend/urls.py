from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('authentication/', include('backend.apps.authentication.urls')),
    path('classrooms/', include('backend.apps.classrooms.urls')),
    path('courses/', include('backend.apps.courses.urls')),
    path('leaderboard/', include('backend.apps.leaderboard.urls')),
    path('achievements/', include('backend.apps.achievements.urls')),
    path('payments/', include('backend.apps.payments.urls')),
    path('contracts/', include('backend.apps.contracts.urls')),
  
]