#!/usr/bin/env bash
# exit on error
set -o errexit

# Verbose output
set -x

echo "==================== START OF BUILD PROCESS ===================="

# Update pip first
echo "Updating pip..."
pip install --upgrade pip

# Check if Django is installed and uninstall it before installing from requirements.txt
echo "Checking for existing Django installations..."
pip uninstall -y django || echo "Django not previously installed"

echo "Installing compatibility-critical packages first..."
pip install --no-cache-dir -r requirements-compat.txt

echo "Installing remaining dependencies..."
grep -v "Django\|django-celery-beat" requirements.txt > requirements-remaining.txt
pip install --no-cache-dir -r requirements-remaining.txt

# Print environment info for debugging
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Create directories with proper structure
echo "Creating necessary directories..."
mkdir -p staticfiles/css
mkdir -p staticfiles/js
mkdir -p staticfiles/img
mkdir -p media
# Create logs directory in both project root and /opt/render/project/src/ path for Render
mkdir -p logs
mkdir -p /opt/render/project/src/logs || echo "Could not create logs directory in /opt/render/project/src/ (this is expected in local development)"
# Ensure data directory exists for SQLite persistence
mkdir -p data

# Debug Django settings
echo "Django settings debug:"
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.conf import settings; print(f'DEBUG: {settings.DEBUG}'); print(f'STATIC_ROOT: {settings.STATIC_ROOT}'); print(f'STATICFILES_DIRS: {settings.STATICFILES_DIRS}'); print(f'STATIC_URL: {settings.STATIC_URL}'); print(f'DATABASE: {settings.DATABASES[\"default\"][\"ENGINE\"]}')"

# Check if core static directory exists and its contents
echo "Checking core/static directory..."
if [ -d "core/static" ]; then
    echo "core/static directory exists"
    find core/static -type f | sort
else
    echo "ERROR: core/static directory not found!"
    mkdir -p core/static/css core/static/js core/static/img
fi

# Run our verification script for detailed static file checking
echo "Running static files verification..."
python verify_static.py

# Run collectstatic with verbose output
echo "Running Django collectstatic..."
python manage.py collectstatic --no-input --clear -v 2

# Force manual copy of static files (regardless of collectstatic result)
echo "Manually copying static files as backup..."
# Create directories if they don't exist
mkdir -p staticfiles/css staticfiles/js staticfiles/img

# Copy all static files recursively
echo "Copying all static files from core/static to staticfiles..."
cp -rv core/static/* staticfiles/ || echo "Error copying files"

# Check the result after manual copy
echo "Checking staticfiles after manual copy:"
find staticfiles -type f | sort

# Run verification again after copy
echo "Verifying static files after manual copy..."
python verify_static.py

# Set proper permissions
echo "Setting permissions on staticfiles directory..."
chmod -R 755 staticfiles

# Create .gitkeep files in empty directories to ensure they exist
echo "Creating .gitkeep files in empty directories..."
find staticfiles -type d -empty -exec touch {}/.gitkeep \;

# ===== DATABASE MIGRATIONS =====
echo "===== DATABASE SETUP ====="

# Print database connection info (without credentials)
echo "Database engine configuration:"
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.conf import settings; print(f'Database ENGINE: {settings.DATABASES[\"default\"][\"ENGINE\"]}'); print(f'Using DATABASE_URL: {\"Yes\" if os.environ.get(\"DATABASE_URL\") else \"No\"}')"

# Debug database connection before migrations
echo "Verifying database connection before migrations:"
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.db import connection; cursor = connection.cursor(); print(f'Database connected: {connection.is_usable()}'); print(f'Database vendor: {connection.vendor}');"

# Check if we're using SQLite and ensure the database file is in the persistent data directory
if [[ $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])") == *"sqlite3"* ]]; then
    echo "Using SQLite database. Ensuring database is in persistent storage..."
    
    # Check if db.sqlite3 exists in the project root and move it to data directory if needed
    if [ -f "db.sqlite3" ] && [ ! -f "data/db.sqlite3" ]; then
        echo "Moving SQLite database to persistent storage in data directory..."
        mv db.sqlite3 data/db.sqlite3
        # Create a symlink for compatibility with existing code
        ln -sf data/db.sqlite3 db.sqlite3
    fi
fi

# Check for existing migrations before applying
echo "Checking for existing migrations:"
python manage.py showmigrations

# Make migrations if needed
echo "Running makemigrations to ensure all migrations are created..."
python manage.py makemigrations

# Run migrations with verbosity
echo "Running migrations with verbosity..."
python manage.py migrate --verbosity 2

# Check if migrations were successful by checking for auth_user table
echo "Verifying migrations were successful..."
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"auth_user\";' if 'sqlite' in connection.vendor else 'SELECT table_name FROM information_schema.tables WHERE table_name = \"auth_user\";'); tables = cursor.fetchall(); print(f'auth_user table exists: {len(tables) > 0}')"

# List all tables in the database to confirm migrations
echo "Listing all database tables after migration:"
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\";' if 'sqlite' in connection.vendor else 'SELECT table_name FROM information_schema.tables WHERE table_schema = \"public\";'); tables = cursor.fetchall(); print('Tables found:'); [print(f'- {table[0]}') for table in tables];"

# Note: Default admin user is now created via migrations (core/migrations/0021_create_default_superuser.py)
# No need to create a superuser here anymore

# ===== POPULATE INITIAL DATA =====
echo "===== POPULATING INITIAL DATA ====="

# Check if personality tests already exist before adding
echo "Checking for existing personality tests..."
TEST_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import PersonalityTest; print(PersonalityTest.objects.count())")

if [ "$TEST_COUNT" -eq "0" ]; then
    echo "No personality tests found. Adding personality tests..."
    python manage.py add_personality_tests
else
    echo "Personality tests already exist (${TEST_COUNT} found). Skipping add_personality_tests."
fi

# Check if mentors already exist before adding
echo "Checking for existing mentors..."
MENTOR_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Mentor; print(Mentor.objects.count())")

if [ "$MENTOR_COUNT" -eq "0" ]; then
    echo "No mentors found. Adding mentors..."
    python manage.py add_mentors
else
    echo "Mentors already exist (${MENTOR_COUNT} found). Skipping add_mentors."
fi

# Final verification
echo "Final verification of static files structure:"
echo "staticfiles directory size: $(du -sh staticfiles)"
find staticfiles -type f | wc -l
echo "==================== END OF BUILD PROCESS ===================="

echo "Build completed successfully!" 