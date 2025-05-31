from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Checks if the social_auth tables exist in the database.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get list of all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            self.stdout.write("Available tables in the database:")
            for table in tables:
                self.stdout.write(f"- {table[0]}")
                
            # Check specifically for social_auth tables
            social_tables = [table[0] for table in tables if 'social_auth' in table[0]]
            
            if social_tables:
                self.stdout.write(self.style.SUCCESS(f"Found {len(social_tables)} social_auth tables:"))
                for table in social_tables:
                    self.stdout.write(f"  - {table}")
            else:
                self.stdout.write(self.style.ERROR("No social_auth tables found!")) 