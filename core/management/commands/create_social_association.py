from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from social_django.models import UserSocialAuth
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates or updates a social authentication association for an existing user'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Email of the user')
        parser.add_argument('--provider', default='google-oauth2', help='OAuth provider (default: google-oauth2)')
        parser.add_argument('--uid', required=True, help='UID from the provider (e.g., Google account ID)')
        
    def handle(self, *args, **options):
        email = options['email']
        provider = options['provider']
        uid = options['uid']
        
        try:
            # Find the user by email
            user = User.objects.get(email=email)
            self.stdout.write(f"Found user: {user.username} (ID: {user.id})")
            
            # Check if association already exists
            existing = UserSocialAuth.objects.filter(user=user, provider=provider).first()
            
            if existing:
                # Update existing association
                existing.uid = uid
                existing.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Updated existing {provider} association for {user.username}"
                ))
            else:
                # Create new association
                UserSocialAuth.objects.create(
                    user=user,
                    provider=provider,
                    uid=uid
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Created new {provider} association for {user.username}"
                ))
                
            return True
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email {email} not found"))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            return False 