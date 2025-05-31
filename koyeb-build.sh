#!/usr/bin/env bash
# Exit on error
set -o errexit

# Verbose output
set -x

echo "===== KOYEB DEPLOYMENT BUILD SCRIPT ====="

# Update pip first
echo "Updating pip..."
pip install --upgrade pip

# Force remove and reinstall Django to the correct version
echo "Forcing Django version ${DJANGO_VERSION:-4.2.11}..."
pip uninstall -y django || echo "Django not previously installed"
pip install Django==${DJANGO_VERSION:-4.2.11} --no-cache-dir

# Install dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --no-cache-dir

# Install social auth packages
echo "Installing social auth packages..."
pip install social-auth-app-django social-auth-core --no-cache-dir

# Print Python and environment info
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Django version: $(python -c 'import django; print(django.__version__)')"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p staticfiles/css
mkdir -p staticfiles/js
mkdir -p staticfiles/img
mkdir -p media
mkdir -p logs

# Debug static files structure before collectstatic
echo "Debugging static files structure before collectstatic..."
find core/static -type f | sort

# Run collectstatic with the default settings
echo "Running collectstatic..."
python manage.py collectstatic --no-input --clear

# Create fix_admin_static.py file inline (reusing from render-build.sh)
echo "Running admin static files fix script..."
python fix_admin_static.py

# Run migrations
echo "Running migrations..."
python manage.py migrate --no-input

# Fix permissions
echo "Fixing permissions..."
chmod -R 755 staticfiles
chmod -R 755 static

echo "Build completed successfully!" 