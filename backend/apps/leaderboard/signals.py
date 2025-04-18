from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender='authentication.Student')
@receiver(pre_save, sender='authentication.Teacher')
@receiver(pre_save, sender='authentication.School')
def check_points_change(sender, instance, **kwargs):
    """Verify if points have changed and log the change"""
    if not instance.pk:  # New instance, no previous points
        return
        
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.points != instance.points:
            logger.info(
                f"Points change detected for {instance.user.id}: "
                f"{old_instance.points} -> {instance.points}"
            )
            # Store the points change on the instance for post_save to use
            instance._points_changed = True
    except sender.DoesNotExist:
        pass

@receiver(post_save, sender='authentication.Student')
@receiver(post_save, sender='authentication.Teacher')
@receiver(post_save, sender='authentication.School')
def update_leaderboard_on_points_change(sender, instance, created, **kwargs):
    """Update leaderboard only if points changed"""
    points_changed = getattr(instance, '_points_changed', False) or created
    
    if not points_changed:
        return
        
    if not hasattr(instance, 'user') or not instance.user:
        logger.warning(f"No user associated with {instance}")
        return
        
    role_map = {
        'Student': 'student',
        'Teacher': 'teacher',
        'School': 'school'
    }
    role = role_map.get(instance.__class__.__name__)
    
    if not role:
        return
        
    def execute_update():
        from .utils import update_leaderboard
        try:
            logger.info(f"Executing leaderboard update for {instance.user.id} with {instance.points} points")
            success = update_leaderboard(instance.user, instance.points, role)
            if not success:
                logger.error(f"Failed to update leaderboard for {instance.user.id}")
        except Exception as e:
            logger.error(f"Error in leaderboard update: {str(e)}", exc_info=True)
    
    transaction.on_commit(execute_update)