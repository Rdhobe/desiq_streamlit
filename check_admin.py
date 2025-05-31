import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
import django
django.setup()

from django.contrib.auth.models import User
from core.models import Profile

admin_exists = User.objects.filter(username='admin').exists()
print(f'Admin user exists: {admin_exists}')

if admin_exists:
    admin_user = User.objects.get(username='admin')
    profile_exists = Profile.objects.filter(user=admin_user).exists()
    print(f'Admin profile exists: {profile_exists}')
    
    if profile_exists:
        profile = Profile.objects.get(user=admin_user)
        print(f'Profile is premium: {profile.is_premium}')
        print(f'XP points: {profile.xp_points}')
        print(f'Level: {profile.level}')
        print(f'Rank: {profile.rank}')
        print(f'Total comments: {profile.total_comments}')
        print(f'Total likes received: {profile.total_likes_received}') 