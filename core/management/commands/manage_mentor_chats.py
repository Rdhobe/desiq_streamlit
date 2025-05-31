from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import MentorChat, MentorChatUsage, Mentor
from django.db import models
import datetime

class Command(BaseCommand):
    help = 'Manage mentor chat data with various operations'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Clear old chats command
        clear_parser = subparsers.add_parser('clear-old', help='Clear old chat data')
        clear_parser.add_argument('--days', type=int, default=90, 
                                help='Delete chats older than this many days')
        
        # Reset usage limits command
        reset_parser = subparsers.add_parser('reset-limits', help='Reset daily usage limits')
        reset_parser.add_argument('--username', type=str, 
                                help='Reset limits for a specific user (omit for all users)')
        
        # List chat stats command
        subparsers.add_parser('stats', help='Show chat statistics')
        
        # Copy chats command (for migrating data)
        copy_parser = subparsers.add_parser('copy-chats', help='Copy chat data from one user to another')
        copy_parser.add_argument('--from', dest='from_user', type=str, required=True, 
                               help='Username to copy from')
        copy_parser.add_argument('--to', dest='to_user', type=str, required=True, 
                               help='Username to copy to')

    def handle(self, *args, **options):
        command = options['command']
        
        if command == 'clear-old':
            self.clear_old_chats(options['days'])
        elif command == 'reset-limits':
            self.reset_usage_limits(options.get('username'))
        elif command == 'stats':
            self.show_stats()
        elif command == 'copy-chats':
            self.copy_chats(options['from_user'], options['to_user'])
        else:
            self.stdout.write(self.style.ERROR('Please specify a valid command'))
    
    def clear_old_chats(self, days):
        """Delete chat messages older than the specified number of days"""
        cutoff_date = timezone.now() - datetime.timedelta(days=days)
        
        count, _ = MentorChat.objects.filter(timestamp__lt=cutoff_date).delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {count} chat messages older than {days} days'
        ))
    
    def reset_usage_limits(self, username=None):
        """Reset the daily usage limits for users"""
        today = timezone.now().date()
        
        if username:
            try:
                user = User.objects.get(username=username)
                count, _ = MentorChatUsage.objects.filter(user=user, date=today).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully reset daily chat limits for user {username}'
                ))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {username} does not exist'))
        else:
            count, _ = MentorChatUsage.objects.filter(date=today).delete()
            self.stdout.write(self.style.SUCCESS(
                f'Successfully reset daily chat limits for all users'
            ))
    
    def show_stats(self):
        """Show chat statistics"""
        total_chats = MentorChat.objects.count()
        total_users = User.objects.filter(mentor_chats__isnull=False).distinct().count()
        total_mentors = Mentor.objects.filter(chats__isnull=False).distinct().count()
        
        # Most popular mentors
        popular_mentors = Mentor.objects.annotate(
            chat_count=models.Count('chats')
        ).order_by('-chat_count')[:5]
        
        # Recent activity
        today = timezone.now().date()
        chats_today = MentorChat.objects.filter(timestamp__date=today).count()
        
        self.stdout.write(self.style.SUCCESS('Chat Statistics:'))
        self.stdout.write(f'Total chat messages: {total_chats}')
        self.stdout.write(f'Users who have chatted: {total_users}')
        self.stdout.write(f'Active mentors: {total_mentors}')
        self.stdout.write(f'Chat messages today: {chats_today}')
        
        self.stdout.write('\nMost Popular Mentors:')
        for mentor in popular_mentors:
            self.stdout.write(f'- {mentor.name}: {mentor.chat_count} messages')
    
    def copy_chats(self, from_username, to_username):
        """Copy chat data from one user to another"""
        try:
            from_user = User.objects.get(username=from_username)
            to_user = User.objects.get(username=to_username)
            
            chats = MentorChat.objects.filter(user=from_user)
            chat_count = chats.count()
            
            for chat in chats:
                # Create a copy of the chat with the new user
                MentorChat.objects.create(
                    user=to_user,
                    mentor=chat.mentor,
                    message=chat.message,
                    message_type=chat.message_type,
                    timestamp=chat.timestamp
                )
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully copied {chat_count} chat messages from {from_username} to {to_username}'
            ))
            
        except User.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'User does not exist: {str(e)}')) 