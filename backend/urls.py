from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('authentication/', include('backend.apps.authentication.urls')),  # Include authentication URLs
  
]
