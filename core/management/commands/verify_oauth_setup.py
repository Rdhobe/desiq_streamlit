from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Verifies OAuth configuration and sets credentials if needed'

    def add_arguments(self, parser):
        parser.add_argument('--google-key', type=str, help='Google OAuth2 Client ID')
        parser.add_argument('--google-secret', type=str, help='Google OAuth2 Client Secret')
        parser.add_argument('--verify-only', action='store_true', help='Only verify, do not update')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Checking OAuth setup..."))
        
        # Check Google OAuth credentials
        google_key = options.get('google_key')
        google_secret = options.get('google_secret')
        verify_only = options.get('verify_only', False)
        
        # Get current values
        current_key = getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
        current_secret = getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')
        
        if current_key:
            self.stdout.write(self.style.SUCCESS(f"✅ GOOGLE_OAUTH2_KEY is set [{current_key[:5]}...]"))
        else:
            self.stdout.write(self.style.ERROR("❌ GOOGLE_OAUTH2_KEY is not set"))
            
        if current_secret:
            self.stdout.write(self.style.SUCCESS(f"✅ GOOGLE_OAUTH2_SECRET is set [{current_secret[:3]}...]"))
        else:
            self.stdout.write(self.style.ERROR("❌ GOOGLE_OAUTH2_SECRET is not set"))
        
        # Update credentials if provided
        if not verify_only and (google_key or google_secret):
            self.stdout.write("Updating OAuth credentials...")
            
            if google_key:
                os.environ['GOOGLE_OAUTH2_KEY'] = google_key
                self.stdout.write(self.style.SUCCESS(f"Updated GOOGLE_OAUTH2_KEY to {google_key[:5]}..."))
                
            if google_secret:
                os.environ['GOOGLE_OAUTH2_SECRET'] = google_secret
                self.stdout.write(self.style.SUCCESS(f"Updated GOOGLE_OAUTH2_SECRET to {google_secret[:3]}..."))
                
            self.stdout.write(self.style.WARNING(
                "Note: These updates are only for the current process. "
                "To make them permanent, set them in your environment."
            ))
        
        # Check if OAuth is properly configured
        from social_core.backends.utils import load_backends
        self.stdout.write("\nVerifying backend registration...")
        
        try:
            backends = load_backends(settings.AUTHENTICATION_BACKENDS)
            self.stdout.write(f"Registered backends: {list(backends.keys())}")
            
            if 'google-oauth2' in backends:
                self.stdout.write(self.style.SUCCESS("✅ google-oauth2 backend is properly registered"))
            else:
                self.stdout.write(self.style.ERROR("❌ google-oauth2 backend is NOT registered"))
            
            # Try to import GoogleOAuth2 backend
            from social_core.backends.google import GoogleOAuth2
            self.stdout.write(self.style.SUCCESS("✅ GoogleOAuth2 class imported successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking backends: {e}"))
        
        self.stdout.write("\nOAuth verification complete") 