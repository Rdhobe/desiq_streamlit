#!/usr/bin/env bash
# Master script to set up all demo data for the application

# Exit on error
set -e

echo "==============================================="
echo "DESIQ DEMO DATA SETUP"
echo "==============================================="

# Make sure we're in the project directory
cd "$(dirname "$0")"

# Check if Django is installed
if ! python -c "import django" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run migrations if needed
echo "Checking and running migrations..."
python manage.py migrate

# Add personality tests
echo "Adding personality tests..."
python manage.py add_personality_tests

# Add mentors
echo "Adding mentors..."
python manage.py add_mentors

# Add test scenarios
echo "Adding test scenarios..."
python manage.py add_test_scenarios --count 30

# Add fake users and their progress
echo "Adding fake users and their progress..."
chmod +x populate_fake_users.sh
./populate_fake_users.sh

echo "==============================================="
echo "DEMO DATA SETUP COMPLETE"
echo "==============================================="
echo "Summary:"
echo "- Users: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.contrib.auth.models import User; print(User.objects.count())")"
echo "- Premium Users: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Profile; print(Profile.objects.filter(is_premium=True).count())")"
echo "- Scenarios: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Scenario; print(Scenario.objects.count())")"
echo "- Personality Tests: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import PersonalityTest; print(PersonalityTest.objects.count())")"
echo "- Mentors: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Mentor; print(Mentor.objects.count())")"
echo "===============================================" 