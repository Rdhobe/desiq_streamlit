#!/usr/bin/env python
"""
PostgreSQL verification utility for DesiQ.
Checks database connection and tables.

Usage:
  python verify_postgres.py
"""

import os
import sys
import django
from pathlib import Path

# Disable dotenv loading to avoid encoding issues
os.environ["DISABLE_DOTENV"] = "True"

def verify_postgres():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
    
    try:
        django.setup()
    except Exception as e:
        print(f"Error during Django setup: {e}")
        return False
    
    # Import Django modules after setup
    from django.db import connection, DatabaseError, OperationalError
    from django.conf import settings
    
    print("=" * 80)
    print("POSTGRESQL VERIFICATION UTILITY")
    print("=" * 80)
    
    # Print database configuration (without credentials)
    db_config = settings.DATABASES['default']
    db_engine = db_config.get('ENGINE', 'unknown')
    
    if 'postgresql' not in db_engine:
        print(f"❌ Not using PostgreSQL! Current engine: {db_engine}")
        return False
    
    print(f"✅ Using PostgreSQL engine: {db_engine}")
    
    # Check database connectivity
    print("\nChecking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version}")
    except (DatabaseError, OperationalError) as e:
        print(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check database tables
    print("\nChecking database tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = [table[0] for table in cursor.fetchall()]
            
            print(f"Total tables found: {len(tables)}")
            if tables:
                print("Tables in database:")
                for table in sorted(tables):
                    print(f"  - {table}")
            
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
        import traceback
        traceback.print_exc()
        return False
    
    # Check model data
    print("\nChecking model data...")
    try:
        from django.contrib.auth.models import User
        
        user_count = User.objects.count()
        print(f"User count: {user_count}")
        
        # Try to check some application-specific models
        try:
            from core.models import Profile, Scenario, Mentor
            
            profile_count = Profile.objects.count()
            scenario_count = Scenario.objects.count()
            mentor_count = Mentor.objects.count()
            
            print(f"Profile count: {profile_count}")
            print(f"Scenario count: {scenario_count}")
            print(f"Mentor count: {mentor_count}")
            
            if profile_count > 0 and user_count > 0:
                print("✅ Data appears to be properly migrated")
            else:
                print("⚠️ Tables exist but may not contain data. Check if migration was completed.")
        except ImportError:
            print("⚠️ Could not import application models. Skipping specific model checks.")
    except Exception as e:
        print(f"❌ Error checking model data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ PostgreSQL verification completed successfully!")
    return True

if __name__ == "__main__":
    success = verify_postgres()
    
    if success:
        print("\n✅ Your application is properly configured for PostgreSQL!")
        print("You can now deploy to Render with confidence.")
        sys.exit(0)
    else:
        print("\n❌ PostgreSQL verification failed! Fix the issues before deploying.")
        sys.exit(1) 