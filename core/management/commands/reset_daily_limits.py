from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import DailyUsageTracker
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reset daily usage limits for all users'

    def handle(self, *args, **options):
        today = timezone.now().date()
        yesterday = today - timezone.timedelta(days=1)
        
        # Get all trackers from yesterday or earlier
        old_trackers = DailyUsageTracker.objects.filter(date__lt=today)
        count = old_trackers.count()
        
        if count > 0:
            # Delete old trackers to reset limits
            old_trackers.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully reset daily limits for {count} users'))
            logger.info(f'Daily limits reset for {count} users')
        else:
            self.stdout.write(self.style.SUCCESS('No daily limits to reset'))
            logger.info('No daily limits to reset') 