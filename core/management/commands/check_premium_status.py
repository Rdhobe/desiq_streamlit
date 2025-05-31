from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Check a user\'s premium status and optionally set them as premium'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to check')
        parser.add_argument(
            '--set-premium',
            action='store_true',
            help='Set the user as premium',
        )
        parser.add_argument(
            '--plan',
            type=str,
            choices=['monthly', 'annual'],
            default='monthly',
            help='Premium plan type (monthly or annual)',
        )

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        set_premium = kwargs['set_premium']
        plan = kwargs['plan']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        profile = user.profile
        
        # Display current status
        self.stdout.write(f"User: {user.username} (ID: {user.id})")
        self.stdout.write(f"Premium status: {profile.is_premium}")
        self.stdout.write(f"Plan: {profile.premium_plan or 'None'}")
        self.stdout.write(f"Expires: {profile.premium_expires or 'Not set'}")
        self.stdout.write(f"Payment method ID: {profile.payment_method_id or 'None'}")
        self.stdout.write(f"Stripe subscription ID: {profile.stripe_subscription_id or 'None'}")
        
        # Calculate if subscription is active
        active_subscription = False
        if profile.is_premium and profile.premium_expires:
            if profile.premium_expires > timezone.now():
                active_subscription = True
                days_left = (profile.premium_expires - timezone.now()).days
                self.stdout.write(f"Active subscription: Yes (expires in {days_left} days)")
            else:
                self.stdout.write(f"Active subscription: No (expired)")
        else:
            self.stdout.write("Active subscription: No")
            
        # Set user as premium if requested
        if set_premium:
            duration_days = 30 if plan == 'monthly' else 365
            profile.is_premium = True
            profile.premium_plan = plan
            
            # Set expiration date
            if profile.premium_expires and profile.premium_expires > timezone.now():
                # Extend existing subscription
                profile.premium_expires = profile.premium_expires + datetime.timedelta(days=duration_days)
            else:
                # New subscription
                profile.premium_expires = timezone.now() + datetime.timedelta(days=duration_days)
            
            profile.payment_method_id = 'manual_upgrade'
            profile.save()
            
            self.stdout.write(self.style.SUCCESS(f"Successfully set {username} as premium ({plan} plan)"))
            self.stdout.write(f"New expiration date: {profile.premium_expires}") 