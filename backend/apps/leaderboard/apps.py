# backend/apps/leaderboard/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class LeaderboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.leaderboard'
    
    def ready(self):
        """
        Initialize leaderboard when Django starts.
        Uses lazy imports to prevent circular imports.
        """
        try:
            # Import inside ready() to avoid AppRegistryNotReady issues
            from django.db.models.signals import post_migrate
            
            # Connect signals after models are loaded
            self.connect_signals()
            
            # Initialize indexes after migrations complete
            post_migrate.connect(self.init_leaderboard, sender=self)
            
            logger.info("Leaderboard app initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize leaderboard: {str(e)}", exc_info=True)
            raise
    
    def connect_signals(self):
        """Connect signals after models are ready"""
        from . import signals  # noqa
        logger.debug("Leaderboard signals connected")
    
    def init_leaderboard(self, sender, **kwargs):
        """Initialize leaderboard indexes and existing users after migrations"""
        try:
            from .utils import ensure_indexes, init_existing_users
            ensure_indexes()
            
            # Only init users during actual migrations, not during runserver
            if kwargs.get('verbosity', 0) > 0:
                init_existing_users()
                
            logger.info("Leaderboard indexes and users initialized")
        except Exception as e:
            logger.error(f"Leaderboard initialization failed: {str(e)}", exc_info=True)