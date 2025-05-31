from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import DailyChallenge, Profile
from core.utils import generate_daily_challenges_for_user

class Command(BaseCommand):
    help = 'Generate daily challenges for all users'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of challenges even if they already exist for today',
        )
        
        parser.add_argument(
            '--user_id',
            type=int,
            help='Generate challenges for a specific user ID',
        )
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        force = options.get('force', False)
        user_id = options.get('user_id')
        
        if user_id:
            try:
                users = [User.objects.get(id=user_id)]
                self.stdout.write(f"Generating challenges for user ID {user_id}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} does not exist"))
                return
        else:
            users = User.objects.all()
            self.stdout.write(f"Generating challenges for all users ({users.count()} users found)")
        
        for user in users:
            # Check if user already has challenges for today
            existing_challenges = DailyChallenge.objects.filter(
                user=user,
                date_created=today
            ).count()
            
            if existing_challenges > 0 and not force:
                self.stdout.write(f"User {user.username} already has {existing_challenges} challenges for today. Skipping.")
                continue
            
            # Delete existing challenges if force is True
            if force and existing_challenges > 0:
                DailyChallenge.objects.filter(user=user, date_created=today).delete()
                self.stdout.write(f"Deleted existing challenges for user {user.username}")
            
            # Determine number of challenges based on premium status
            is_premium = hasattr(user, 'profile') and user.profile.is_premium
            num_challenges = 3 if is_premium else 1
            
            try:
                # Generate challenges
                challenges = generate_daily_challenges_for_user(user, num_challenges)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated {len(challenges)} challenges for user {user.username}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error generating challenges for user {user.username}: {str(e)}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('Daily challenges generation complete')) 