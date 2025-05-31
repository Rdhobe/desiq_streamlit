from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
import importlib
import sys
import traceback


class Command(BaseCommand):
    help = 'Checks the social auth setup and backends configuration.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Checking social auth setup..."))
        
        # 1. Check if the required apps are installed
        self.stdout.write("1. Checking installed apps...")
        for app in ['social_django', 'social_core']:
            try:
                importlib.import_module(app)
                self.stdout.write(self.style.SUCCESS(f"✅ {app} is installed"))
            except ImportError:
                self.stdout.write(self.style.ERROR(f"❌ {app} is NOT installed"))
        
        # 2. Check authentication backends
        self.stdout.write("\n2. Checking authentication backends...")
        if hasattr(settings, 'AUTHENTICATION_BACKENDS'):
            for backend in settings.AUTHENTICATION_BACKENDS:
                self.stdout.write(f"- {backend}")
                
                # Try to import each backend
                try:
                    module_path, class_name = backend.rsplit('.', 1)
                    module = importlib.import_module(module_path)
                    backend_class = getattr(module, class_name)
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Backend class {class_name} found"))
                except (ImportError, AttributeError) as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error importing backend: {e}"))
        else:
            self.stdout.write(self.style.ERROR("❌ AUTHENTICATION_BACKENDS not defined in settings"))
        
        # 3. Check if GoogleOAuth2 backend is properly installed
        self.stdout.write("\n3. Checking GoogleOAuth2 backend specifically...")
        try:
            from social_core.backends.google import GoogleOAuth2
            self.stdout.write(self.style.SUCCESS("✅ GoogleOAuth2 backend class exists"))
            
            # Check for google-oauth2 in registered backends
            try:
                from social_core.backends.utils import load_backends
                backends = load_backends(settings.AUTHENTICATION_BACKENDS)
                if 'google-oauth2' in backends:
                    self.stdout.write(self.style.SUCCESS("✅ 'google-oauth2' is in registered backends"))
                else:
                    self.stdout.write(self.style.ERROR("❌ 'google-oauth2' is NOT in registered backends"))
                    
                    # Show what's registered instead
                    self.stdout.write("Registered backend names:")
                    for name in backends:
                        self.stdout.write(f"- {name}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error checking registered backends: {e}"))
                
        except ImportError:
            self.stdout.write(self.style.ERROR("❌ GoogleOAuth2 backend could not be imported"))
        
        # 4. Check social auth database tables
        self.stdout.write("\n4. Checking social auth database tables...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%social%'")
            tables = cursor.fetchall()
            if not tables:
                self.stdout.write(self.style.ERROR("❌ No social auth tables found!"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Found {len(tables)} social tables:"))
                for table in tables:
                    self.stdout.write(f"- {table[0]}")
                    
                # Check required tables specifically
                for table_name in [
                    'social_auth_association',
                    'social_auth_code',
                    'social_auth_nonce',
                    'social_auth_partial',
                    'social_auth_usersocialauth'
                ]:
                    cursor.execute(f"SELECT * FROM pg_tables WHERE tablename = %s", [table_name])
                    if cursor.fetchone():
                        self.stdout.write(self.style.SUCCESS(f"✅ {table_name} exists"))
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ {table_name} missing"))
        
        # 5. Check social auth settings
        self.stdout.write("\n5. Checking social auth settings...")
        for setting_name in [
            'SOCIAL_AUTH_URL_NAMESPACE',
            'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',
            'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET',
            'SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE'
        ]:
            if hasattr(settings, setting_name):
                value = getattr(settings, setting_name)
                # Mask secrets
                if 'SECRET' in setting_name:
                    if value:
                        value = f"{value[:3]}...{value[-3:]}" if len(value) > 6 else "***"
                    else:
                        value = "(empty)"
                self.stdout.write(f"- {setting_name}: {value}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ {setting_name} not defined"))

        # 6. Test loading the backend directly
        self.stdout.write("\n6. Testing backend loading directly...")
        try:
            from social_core.backends.utils import get_backend
            google_backend = get_backend(settings.AUTHENTICATION_BACKENDS, 'google-oauth2')
            self.stdout.write(self.style.SUCCESS(f"✅ Successfully loaded google-oauth2 backend: {google_backend.__class__.__name__}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error loading google-oauth2 backend: {e}"))
            # Print detailed traceback for debugging
            traceback.print_exc(file=sys.stdout)
            
        self.stdout.write(self.style.SUCCESS("\nSocial auth check complete")) 