from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a superuser during deployment if none exists'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help='Username for the superuser'
        )
        parser.add_argument(
            '--email',
            default='admin@example.com',
            help='Email for the superuser'
        )
        parser.add_argument(
            '--password',
            help='Password for the superuser (if not provided, will try to use environment variable)'
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Run without asking for user input'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        noinput = options['noinput']
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            if not noinput:
                self.stdout.write(self.style.WARNING(f'Superuser already exists. Do you want to create another one? (y/n)'))
                answer = input().lower()
                if answer != 'y':
                    self.stdout.write(self.style.SUCCESS('Skipping superuser creation.'))
                    return
            else:
                self.stdout.write(self.style.SUCCESS('Superuser already exists. Skipping creation.'))
                return
        
        # If password not provided as argument, try to get from environment variable
        if not password:
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
            
        # If still no password and not in noinput mode, ask for it
        if not password and not noinput:
            self.stdout.write('Please enter password for the superuser:')
            password = input()
        
        # If still no password, generate a random one
        if not password:
            import random
            import string
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            self.stdout.write(self.style.WARNING(f'Generated random password for superuser: {password}'))
            self.stdout.write(self.style.WARNING('Please change this password after first login!'))
        
        try:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create superuser: {str(e)}'))
            logger.error(f'Failed to create superuser: {str(e)}')
            return 