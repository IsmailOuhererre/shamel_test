# services/email_service.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_verification_email(user, verification_code):
        try:
            subject = "Verify Your Email Address"
            
            # Render HTML and text content
            html_content = render_to_string('emails/verification_email.html', {
                'user': user,
                'verification_code': verification_code
            })
            text_content = strip_tags(render_to_string('emails/verification_email.txt', {
                'user': user,
                'verification_code': verification_code
            }))
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            logger.info(f"Verification email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False

    @staticmethod
    def send_password_reset_email(user, reset_code):
        try:
            subject = "Password Reset Request"
            
            # Render HTML and text content
            html_content = render_to_string('emails/password_reset_email.html', {
                'user': user,
                'reset_code': reset_code
            })
            text_content = strip_tags(render_to_string('emails/password_reset_email.txt', {
                'user': user,
                'reset_code': reset_code
            }))
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            logger.info(f"Password reset email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False