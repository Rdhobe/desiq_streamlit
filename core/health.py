"""
Health check endpoints for monitoring system status.
"""
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.template.loader import get_template
import time
import logging
import os
import sys
import traceback
import importlib

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Health check endpoint for monitoring.
    Checks database connection, returns 200 if healthy.
    """
    # Capture start time for response time metric
    start_time = time.time()
    
    # Check database connection
    db_healthy = False
    db_error = None
    try:
        # Execute a simple query to check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            db_healthy = result and result[0] == 1
    except Exception as e:
        db_error = str(e)
        logger.error(f"Health check database error: {str(e)}")
    
    # Check template rendering
    template_healthy = False
    template_error = None
    try:
        # Try to load a template to verify template system works
        template = get_template('core/base.html')
        template_healthy = True
    except Exception as e:
        template_error = str(e)
        logger.error(f"Health check template error: {str(e)}")
    
    # Check error template specifically
    error_template_healthy = False
    error_template_msg = None
    try:
        # Try to load the 500 error template
        template = get_template('core/500.html')
        error_template_healthy = True
    except Exception as e:
        error_template_msg = str(e)
        logger.error(f"Health check 500 template error: {str(e)}")
    
    # Check URL resolution
    url_healthy = False
    url_error = None
    try:
        # Try to import urls module and check handler500
        from django.urls import get_resolver
        resolver = get_resolver()
        handler500 = getattr(resolver.urlconf_module, 'handler500', None)
        url_healthy = handler500 is not None
        if not url_healthy:
            url_error = "handler500 not defined in URLs"
    except Exception as e:
        url_error = str(e)
        logger.error(f"Health check URL resolution error: {str(e)}")
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Add environment info
    env_info = {
        "python_version": sys.version,
        "django_version": importlib.import_module('django').__version__,
        "template_dirs": settings.TEMPLATES[0]['DIRS'],
        "app_dirs": settings.TEMPLATES[0]['APP_DIRS'],
        "debug": settings.DEBUG,
        "static_root": settings.STATIC_ROOT,
        "media_root": settings.MEDIA_ROOT
    }
    
    # Build health data
    health_data = {
        "status": "healthy" if (db_healthy and template_healthy and error_template_healthy and url_healthy) else "unhealthy",
        "database": {
            "status": "connected" if db_healthy else "disconnected",
            "error": db_error
        },
        "templates": {
            "status": "ok" if template_healthy else "error",
            "error": template_error
        },
        "error_template": {
            "status": "ok" if error_template_healthy else "error",
            "error": error_template_msg
        },
        "url_resolution": {
            "status": "ok" if url_healthy else "error",
            "error": url_error
        },
        "environment": env_info,
        "timestamp": time.time(),
        "response_time_ms": round(response_time * 1000, 2)
    }
    
    # If unhealthy, set appropriate status code
    status_code = 200 if health_data["status"] == "healthy" else 503
    
    return JsonResponse(health_data, status=status_code, json_dumps_params={'indent': 2}) 