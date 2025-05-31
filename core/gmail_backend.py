from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from .gmail_service import send_email


class GmailApiEmailBackend(BaseEmailBackend):
    """Custom email backend that uses the Gmail API."""
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.fail_silently = fail_silently
    
    def send_messages(self, email_messages):
        """Send email messages via Gmail API."""
        if not email_messages:
            return 0
        
        sent_count = 0
        
        for message in email_messages:
            try:
                # Get recipients
                recipients = message.to
                if not recipients:
                    continue
                
                # Format message
                to_emails = ', '.join(recipients)
                subject = message.subject
                body = message.body
                from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
                
                # Send email using Gmail API
                result = send_email(to_emails, subject, body, from_email)
                
                if result:
                    sent_count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        
        return sent_count 