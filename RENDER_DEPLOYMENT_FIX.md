# Fixing Django Version Conflicts on Render

This document explains how we resolved Django version conflicts when deploying to Render.

## Problem

The project encountered dependency conflicts during deployment to Render because:

- django-celery-beat 2.5.0 requires Django < 5.0
- Our project was initially set up with Django 5.1.3
- This led to installation failures during the build process

## Solution

### 1. Created Render-specific files

- `render-requirements.txt`: A separate requirements file that explicitly specifies Django 4.2.11
- `render-build.sh`: A custom build script specifically for Render deployment

### 2. Modified Render configuration

Updated `render.yaml` to:
- Use the custom build script (`render-build.sh`) 
- Add an environment variable `DJANGO_VERSION=4.2.11`

### 3. Build Script Details

The build script ensures Django is properly installed:
- Uninstalls any existing Django version first
- Installs Django 4.2.11 explicitly
- Then installs other dependencies from `render-requirements.txt`

## Why Django 4.2.11?

Django 4.2.11 was selected because:
- It's an LTS (Long Term Support) version with security updates until April 2026
- It's compatible with django-celery-beat 2.5.0 which requires Django < 5.0
- It's stable and well-supported

## Future Updates

If you need to upgrade Django in the future:
1. Check compatibility with all dependencies
2. Update both `requirements.txt` and `render-requirements.txt`
3. Update the `DJANGO_VERSION` environment variable in `render.yaml` 