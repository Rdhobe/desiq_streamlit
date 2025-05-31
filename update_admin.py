import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
import django
django.setup()

from django.contrib.auth.models import User
from core.models import Profile
from django.utils import timezone

# Get the admin user
try:
    admin_user = User.objects.get(username='admin')
    print(f"Found admin user: {admin_user.username}")
    
    # Get or create the admin profile
    profile, created = Profile.objects.get_or_create(user=admin_user)
    if created:
        print("Created new profile for admin")
    else:
        print("Found existing profile for admin")
    
    # Update the profile with the correct values
    profile.is_premium = True
    profile.xp_points = 1000
    profile.rationality_score = 100
    profile.decisiveness_score = 100
    profile.empathy_score = 100
    profile.clarity_score = 100
    profile.level = 10
    profile.daily_streak = 1
    profile.last_login_date = timezone.now().date()
    profile.last_activity = timezone.now()
    profile.rank = 0
    profile.total_comments = 0
    profile.total_likes_received = 0
    profile.total_posts = 0
    profile.total_scenarios_completed = 0
    profile.save()
    
    print("Admin profile updated successfully")
    
    # Verify the profile was updated
    profile = Profile.objects.get(user=admin_user)
    print(f'Profile is premium: {profile.is_premium}')
    print(f'XP points: {profile.xp_points}')
    print(f'Level: {profile.level}')
    
except User.DoesNotExist:
    print("Admin user does not exist") 