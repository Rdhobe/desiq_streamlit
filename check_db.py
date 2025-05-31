#!/usr/bin/env python
"""
Database check utility for Django project.
Runs database migrations if needed.

Usage:
  python check_db.py
"""

import os
import sys
import traceback
import django
from pathlib import Path

def check_database():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
    django.setup()
    
    # Import Django modules after setup
    from django.db import connection, DatabaseError, OperationalError
    from django.conf import settings
    from django.core.management import call_command

    print("=" * 80)
    print("DATABASE CHECK UTILITY")
    print("=" * 80)
    
    # Print database configuration (without credentials)
    db_config = settings.DATABASES['default']
    db_engine = db_config.get('ENGINE', 'unknown')
    db_name = db_config.get('NAME', 'unknown')
    db_host = db_config.get('HOST', 'localhost')
    db_using_url = bool(os.environ.get('DATABASE_URL'))
    
    print(f"Database engine: {db_engine}")
    if db_using_url:
        print(f"Using DATABASE_URL environment variable")
    else:
        print(f"Database name: {db_name}")
        print(f"Database host: {db_host or 'localhost'}")
    
    # Check database connectivity
    print("\nChecking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Database connection successful!")
            else:
                print("❌ Database connection test failed!")
                return False
    except (DatabaseError, OperationalError) as e:
        print(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False
    
    # Check database tables
    print("\nChecking database tables...")
    django_tables = []
    try:
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            else:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            
            tables = [table[0] for table in cursor.fetchall()]
            django_tables = [table for table in tables if not table.startswith('sqlite_') and table != 'django_migrations']
            
            print(f"Total tables found: {len(django_tables)}")
            if django_tables:
                print("Sample tables:")
                for table in django_tables[:5]:
                    print(f"  - {table}")
                if len(django_tables) > 5:
                    print(f"  - ... and {len(django_tables) - 5} more tables")
            
            # Check for essential Django tables
            essential_tables = ['auth_user', 'django_content_type', 'auth_permission']
            missing_tables = [table for table in essential_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing essential tables: {', '.join(missing_tables)}")
                print("Database migrations need to be applied!")
                return False
            else:
                print("✅ All essential Django tables exist")
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        traceback.print_exc()
        return False
    
    # Check migrations
    print("\nChecking migrations status...")
    try:
        # Get migration status
        call_command('showmigrations')
        
        # Ask to run migrations if needed
        if missing_tables:
            print("\nWould you like to run migrations now? (y/n)")
            response = input().lower()
            
            if response == 'y':
                print("\nRunning migrations...")
                call_command('migrate', verbosity=2, interactive=False)
                print("Migrations complete!")
                return True
    except Exception as e:
        print(f"❌ Error with migrations: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = check_database()
    
    if success:
        print("\n✅ Database check completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database check failed! Please fix the issues and try again.")
        sys.exit(1) 