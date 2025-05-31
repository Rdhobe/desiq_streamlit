#!/usr/bin/env python
"""
Render configuration check utility for DesiQ.
Verifies render.yaml and settings for PostgreSQL deployment.

Usage:
  python check_render_config.py
"""

import os
import sys
import yaml
import re

def check_render_config():
    print("=" * 80)
    print("RENDER CONFIGURATION CHECK UTILITY")
    print("=" * 80)
    
    # Check if render.yaml exists
    if not os.path.exists('render.yaml'):
        print("❌ render.yaml file not found!")
        return False
    
    # Parse render.yaml
    try:
        with open('render.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✅ render.yaml loaded successfully")
    except Exception as e:
        print(f"❌ Error parsing render.yaml: {e}")
        return False
    
    # Check if PostgreSQL database is defined
    if 'databases' not in config:
        print("❌ No databases defined in render.yaml")
        return False
    
    db_defined = False
    for db in config['databases']:
        if db.get('name') == 'desiq_db':
            db_defined = True
            print(f"✅ PostgreSQL database defined: {db.get('name')}")
            print(f"  - Plan: {db.get('plan', 'not specified')}")
            print(f"  - Database Name: {db.get('databaseName', 'not specified')}")
            print(f"  - User: {db.get('user', 'not specified')}")
    
    if not db_defined:
        print("❌ desiq_db not defined in render.yaml")
        return False
    
    # Check web service configuration
    if 'services' not in config:
        print("❌ No services defined in render.yaml")
        return False
    
    env_vars_to_check = {
        'DATABASE_URL': False,
        'DB_DIR': False,  # This should not be present
        'sqlite_db': False  # This disk should not be present
    }
    
    for service in config['services']:
        if service.get('type') == 'web' and service.get('name') == 'desiq':
            print(f"✅ Web service defined: {service.get('name')}")
            
            # Check environment variables
            if 'envVars' in service:
                for env_var in service['envVars']:
                    if env_var.get('key') == 'DATABASE_URL' and 'fromDatabase' in env_var:
                        env_vars_to_check['DATABASE_URL'] = True
                    elif env_var.get('key') == 'DB_DIR':
                        env_vars_to_check['DB_DIR'] = True
            
            # Check disks
            if 'disks' in service:
                for disk in service['disks']:
                    if disk.get('name') == 'sqlite_db':
                        env_vars_to_check['sqlite_db'] = True
    
    # Report findings
    if env_vars_to_check['DATABASE_URL']:
        print("✅ DATABASE_URL environment variable properly configured")
    else:
        print("❌ DATABASE_URL not properly configured")
        return False
    
    if env_vars_to_check['DB_DIR']:
        print("❌ DB_DIR environment variable should be removed for PostgreSQL")
        return False
    else:
        print("✅ DB_DIR environment variable not present (good)")
    
    if env_vars_to_check['sqlite_db']:
        print("❌ sqlite_db disk should be removed for PostgreSQL")
        return False
    else:
        print("✅ sqlite_db disk not present (good)")
    
    # Check Django settings.py for PostgreSQL configuration
    print("\nChecking Django settings.py...")
    
    try:
        settings_path = os.path.join('desiq', 'settings.py')
        if not os.path.exists(settings_path):
            print(f"❌ Settings file not found at {settings_path}")
            return False
        
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Check for PostgreSQL configuration
        if "'ENGINE': 'django.db.backends.postgresql'" in settings_content:
            print("✅ PostgreSQL engine properly configured in settings.py")
        else:
            # Use regex to find any PostgreSQL engine specification
            postgres_pattern = r"'ENGINE':\s*'django\.db\.backends\.postgresql(_psycopg2)?'"
            if re.search(postgres_pattern, settings_content):
                print("✅ PostgreSQL engine found in settings.py")
            else:
                print("❌ PostgreSQL engine not found in settings.py")
                return False
        
        # Check for DATABASE_URL handling
        if "dj_database_url.config" in settings_content:
            print("✅ dj_database_url.config found for handling DATABASE_URL")
        else:
            print("❌ dj_database_url.config not found - needed for Render")
            return False
    
    except Exception as e:
        print(f"❌ Error checking settings.py: {e}")
        return False
    
    print("\n✅ Render configuration check completed successfully!")
    return True

if __name__ == "__main__":
    try:
        import yaml
    except ImportError:
        print("PyYAML is required. Install it with: pip install pyyaml")
        sys.exit(1)
    
    success = check_render_config()
    
    if success:
        print("\n✅ Your application is properly configured for Render deployment with PostgreSQL!")
        print("You can now deploy to Render with confidence.")
        sys.exit(0)
    else:
        print("\n❌ Render configuration check failed! Fix the issues before deploying.")
        sys.exit(1) 