from django.db import migrations
from django.contrib.auth.hashers import make_password
from django.utils import timezone


def create_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('core', 'Profile')
    
    # Check if the superuser already exists
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@desiq.live',
            'password': make_password('DesiqAdmin123!'),
            'is_staff': True,
            'is_active': True,
            'is_superuser': True
        }
    )
    
    if created:
        print("Created new admin user")
    else:
        print("Admin user already exists")
    
    # Get or create a profile for the admin user
    profile, profile_created = Profile.objects.get_or_create(
        user=admin_user
    )
    
    # Always update the profile with the correct values
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
    
    if profile_created:
        print("Created new profile for admin")
    else:
        print("Updated existing profile for admin")


def reverse_migration(apps, schema_editor):
    # We don't want to delete the admin user if it's being used
    # This is a safer approach for production
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_alter_useractivity_activity_type'),
    ]

    operations = [
        migrations.RunPython(create_superuser, reverse_migration),
    ] 