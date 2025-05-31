from django.http import HttpResponse
import os
import sys
import json
from django.conf import settings

def debug_info(request):
    """Simple view that returns debug information as plaintext."""
    # Collect information
    info = {
        "request": {
            "path": request.path,
            "method": request.method,
            "scheme": request.scheme,
            "host": request.get_host(),
            "is_secure": request.is_secure(),
            "META": {k: str(v) for k, v in request.META.items() if k.startswith('HTTP_') or k in ('REMOTE_ADDR', 'SERVER_NAME', 'SERVER_PORT')}
        },
        "settings": {
            "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
            "DEBUG": settings.DEBUG,
            "SECURE_SSL_REDIRECT": getattr(settings, 'SECURE_SSL_REDIRECT', None),
            "SECURE_PROXY_SSL_HEADER": getattr(settings, 'SECURE_PROXY_SSL_HEADER', None),
            "USE_X_FORWARDED_HOST": getattr(settings, 'USE_X_FORWARDED_HOST', None),
            "USE_X_FORWARDED_PORT": getattr(settings, 'USE_X_FORWARDED_PORT', None),
            "STATIC_URL": settings.STATIC_URL,
            "STATIC_ROOT": settings.STATIC_ROOT
        },
        "env": {
            "DJANGO_SETTINGS_MODULE": os.environ.get('DJANGO_SETTINGS_MODULE', 'Not set'),
            "PYTHONPATH": os.environ.get('PYTHONPATH', 'Not set'),
            "PORT": os.environ.get('PORT', 'Not set'),
            "DATABASE_URL": os.environ.get('DATABASE_URL', 'Not set').replace(':', '***:***@') if os.environ.get('DATABASE_URL') else 'Not set'
        },
        "system": {
            "python": sys.version,
            "platform": sys.platform,
            "cwd": os.getcwd()
        }
    }
    
    # Return as plaintext
    response_text = "DEBUG INFORMATION\n\n"
    response_text += json.dumps(info, indent=2)
    
    return HttpResponse(response_text, content_type="text/plain") 