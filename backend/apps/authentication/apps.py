from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.authentication'  # ✅ Ensure this matches `INSTALLED_APPS`
