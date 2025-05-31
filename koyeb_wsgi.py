"""
WSGI config for Koyeb deployment.
This is a simplified version that uses our Koyeb-specific settings.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'koyeb_settings')

print("Using Koyeb WSGI configuration")
print(f"DJANGO_SETTINGS_MODULE={os.environ.get('DJANGO_SETTINGS_MODULE')}")

application = get_wsgi_application() 