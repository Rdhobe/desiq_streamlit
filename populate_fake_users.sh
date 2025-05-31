#!/usr/bin/env bash
# Script to populate the database with fake users and their progress

# Exit on error
set -e

echo "Starting fake user population process..."

# Check if the Faker package is installed
pip install Faker

# Check current user count
CURRENT_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.contrib.auth.models import User; print(User.objects.count())")
TARGET_COUNT=2000

echo "Current user count: $CURRENT_COUNT"
echo "Target user count: $TARGET_COUNT"

# Check if we need to create users
USERS_CREATED=0
if [ "$CURRENT_COUNT" -lt "$TARGET_COUNT" ]; then
    echo "Running fake user generation command..."
    python manage.py add_fake_users --count $TARGET_COUNT
    USERS_CREATED=1
else
    echo "User count already at or above target ($CURRENT_COUNT >= $TARGET_COUNT). Skipping user creation."
fi

# Check if we have scenarios
SCENARIO_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Scenario; print(Scenario.objects.count())")

if [ "$SCENARIO_COUNT" -eq "0" ]; then
    echo "No scenarios found. Creating test scenarios..."
    python manage.py add_test_scenarios --count 30
    
    # Check if scenarios were created
    SCENARIO_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Scenario; print(Scenario.objects.count())")
    
    if [ "$SCENARIO_COUNT" -eq "0" ]; then
        echo "Failed to create scenarios. Exiting."
        exit 1
    fi
fi

# Add user progress
echo "Adding scenario progress for users..."
python manage.py add_user_progress --min-scenarios 5 --max-scenarios 20

echo "Fake user population process completed successfully!"
echo "Total users: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from django.contrib.auth.models import User; print(User.objects.count())")"
echo "Total scenarios: $SCENARIO_COUNT"
echo "Premium users: $(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings'); import django; django.setup(); from core.models import Profile; print(Profile.objects.filter(is_premium=True).count())")" 