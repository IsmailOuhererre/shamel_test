from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

@receiver(post_save, sender=Payment)
def payment_status_handler(sender, instance, **kwargs):
    """
    Handle payment status changes
    """
    if instance.status == 'completed':
        # Log the completion
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Payment {instance.id} completed at {instance.completed_at}")