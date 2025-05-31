# Production settings for Koyeb deployment
import os
from desiq.settings import *

# Add wildcard to allowed hosts to accept Koyeb domain
ALLOWED_HOSTS = ['*']

# Handle URL redirects
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Completely disable all SSL/HTTPS redirects
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False

# Filter out any middleware that might cause redirects
NEW_MIDDLEWARE = []
for middleware in MIDDLEWARE:
    # Skip any middleware that might cause redirects
    if 'SSL' in middleware or 'Redirect' in middleware:
        print(f"Skipping middleware: {middleware}")
        continue
    NEW_MIDDLEWARE.append(middleware)
MIDDLEWARE = NEW_MIDDLEWARE

# Print debug info on startup
print(f"Koyeb settings loaded. ALLOWED_HOSTS={ALLOWED_HOSTS}")
print(f"SECURE_SSL_REDIRECT={SECURE_SSL_REDIRECT}")
print(f"MIDDLEWARE={MIDDLEWARE}")

# Override the ROOT_URLCONF to use our debug-friendly URLs
ROOT_URLCONF = 'koyeb_urls'
print(f"ROOT_URLCONF={ROOT_URLCONF}")

# Debug mode
DEBUG = True 