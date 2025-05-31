# Production settings for Koyeb deployment
import os
from desiq.settings import *

# Add wildcard to allowed hosts to accept Koyeb domain
ALLOWED_HOSTS = ['*']

# Handle URL redirects
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Disable HTTPS redirect if it's enabled in main settings
SECURE_SSL_REDIRECT = False

# Print debug info on startup
print(f"Koyeb settings loaded. ALLOWED_HOSTS={ALLOWED_HOSTS}")
print(f"SECURE_SSL_REDIRECT={SECURE_SSL_REDIRECT}") 