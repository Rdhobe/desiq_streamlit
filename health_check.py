#!/usr/bin/env python
"""
A simple health check script to diagnose deployment issues.
Run this with: python health_check.py
"""
import os
import sys
import socket
import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'koyeb_settings')
django.setup()

print("=== Django Health Check ===")

# Check Django version
print(f"Django version: {django.get_version()}")

# Check Python version
print(f"Python version: {sys.version}")

# Check environment variables
print("\n=== Environment Variables ===")
for key in ['DJANGO_SETTINGS_MODULE', 'DEBUG', 'DATABASE_URL', 'STATIC_ROOT', 'STATIC_URL']:
    print(f"{key}: {os.environ.get(key, 'Not set')}")

# Check Django settings
print("\n=== Django Settings ===")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"DEBUG: {settings.DEBUG}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"SECURE_SSL_REDIRECT: {getattr(settings, 'SECURE_SSL_REDIRECT', 'Not set')}")
print(f"SECURE_PROXY_SSL_HEADER: {getattr(settings, 'SECURE_PROXY_SSL_HEADER', 'Not set')}")
print(f"USE_X_FORWARDED_HOST: {getattr(settings, 'USE_X_FORWARDED_HOST', 'Not set')}")
print(f"ROOT_URLCONF: {settings.ROOT_URLCONF}")

# Check if we can resolve localhost
print("\n=== Network Diagnostics ===")
try:
    host_ip = socket.gethostbyname(socket.gethostname())
    print(f"Host IP: {host_ip}")
except Exception as e:
    print(f"Could not resolve host: {str(e)}")

# Check if port 8000 is being listened on
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("Port 8000 is open")
    else:
        print("Port 8000 is not open")
    s.close()
except Exception as e:
    print(f"Port check error: {str(e)}")

print("\n=== Static Files ===")
try:
    static_dirs = settings.STATICFILES_DIRS
    print(f"STATICFILES_DIRS: {static_dirs}")
    for d in static_dirs:
        if os.path.exists(d):
            print(f"Directory {d} exists")
            count = sum(1 for _ in os.listdir(d))
            print(f"Number of files: {count}")
        else:
            print(f"Directory {d} does not exist")
except Exception as e:
    print(f"Static files check error: {str(e)}")

print("\n=== Media Files ===")
try:
    media_root = settings.MEDIA_ROOT
    print(f"MEDIA_ROOT: {media_root}")
    if os.path.exists(media_root):
        print(f"Directory {media_root} exists")
    else:
        print(f"Directory {media_root} does not exist")
except Exception as e:
    print(f"Media files check error: {str(e)}")

print("\n=== Database ===")
from django.db import connections
for conn_name in connections:
    try:
        conn = connections[conn_name]
        conn.ensure_connection()
        print(f"Connection {conn_name}: OK")
    except Exception as e:
        print(f"Connection {conn_name}: FAILED - {str(e)}")

print("\n=== Health check complete ===") 