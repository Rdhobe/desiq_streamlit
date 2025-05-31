# Static Files Configuration for Render Deployment

This document explains how static files are configured and served in this Django application when deployed on Render.

## Directory Structure

- `/staticfiles/` - The main directory where collected static files are stored
- `/core/static/` - The application-specific static files directory

## Static Files Setup

1. **Settings Configuration**

In `settings.py`, the following settings control static files:

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

2. **WhiteNoise Middleware**

WhiteNoise is configured in the middleware to serve static files efficiently:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after security and before other middleware
    # ... other middleware
]
```

3. **URLs Configuration**

In `urls.py`, static files URLs are added using:

```python
urlpatterns += staticfiles_urlpatterns()
```

4. **WSGI Application**

For Render deployment, the `app.py` file configures WhiteNoise directly:

```python
from whitenoise import WhiteNoise
django_app = get_wsgi_application()
app = application = WhiteNoise(django_app, root='staticfiles/')
app.add_files('staticfiles/', prefix='static/')
```

5. **Build Process**

During the build process (in `build.sh`), static files are collected with:

```bash
python manage.py collectstatic --no-input --clear
```

## Troubleshooting Static Files Issues

If static files are not being served correctly:

1. Check the `staticfiles` directory to ensure files were collected properly
2. Verify that the correct URLs are being used in templates (should start with `/static/`)
3. Look at the server logs for WhiteNoise output
4. Ensure the Render disk configuration is correct
5. Try explicitly including file paths in STATICFILES_DIRS

## Media Files

Media files (user uploads) are configured but require a persistent storage solution:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"
```

For production, consider using a cloud storage service for media files instead of local storage. 