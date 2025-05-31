#!/usr/bin/env python
"""
Script to migrate data from SQLite to PostgreSQL for the DesiQ app
This script will:
1. Export data from SQLite to JSON fixtures
2. Create necessary PostgreSQL database objects
3. Import data from JSON fixtures to PostgreSQL

Usage:
    python migrate_to_postgres.py

Requirements:
    - PostgreSQL installed and running
    - Database credentials configured in .env or as environment variables
    - Django project properly configured
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set environment variables for PostgreSQL
# These will be used when the SQLite flag is not set
os.environ['DB_NAME'] = 'desiq_db'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'postgres'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'

# Function to run shell commands and print output
def run_command(command, description=None):
    if description:
        print(f"\n{description}...")
    
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(f"Output: {result.stdout}")
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    return True

# Main migration function
def migrate_to_postgres():
    # Step 1: Create a backup of SQLite database
    print("\n=== Step 1: Creating backup of SQLite database ===")
    backup_path = os.path.join(BASE_DIR, "db_backup.sqlite3")
    if not run_command(f"copy db.sqlite3 {backup_path}", "Creating SQLite backup"):
        print("Failed to create SQLite backup, but continuing...")
    
    # Step 2: Export data from SQLite to JSON fixtures
    print("\n=== Step 2: Exporting data from SQLite to JSON fixtures ===")
    
    # Set environment variable to use SQLite
    os.environ["USE_SQLITE"] = "True"
    # Disable dotenv loading
    os.environ["DISABLE_DOTENV"] = "True"
    
    # Create fixtures directory if it doesn't exist
    fixtures_dir = os.path.join(BASE_DIR, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # Dump data for all apps
    if not run_command(f"python manage.py dumpdata --exclude auth.permission --exclude contenttypes --exclude sessions --indent 2 > {os.path.join(fixtures_dir, 'all_data.json')}", 
                     "Exporting all data from SQLite"):
        print("Failed to export data from SQLite. Aborting.")
        return False
    
    # Step 3: Configure for PostgreSQL
    print("\n=== Step 3: Configuring for PostgreSQL ===")
    
    # Check if PostgreSQL is installed
    if not run_command("psql --version", "Checking PostgreSQL installation"):
        print("\nERROR: PostgreSQL does not appear to be installed or in your PATH.")
        print("Please install PostgreSQL and make sure it's in your system PATH.")
        print("Download from: https://www.postgresql.org/download/windows/")
        print("\nAfter installation:")
        print("1. Make sure PostgreSQL is running")
        print("2. Add the bin directory to your PATH (e.g., C:\\Program Files\\PostgreSQL\\15\\bin)")
        print("3. Run the setup_postgres.bat script to create the database")
        print("4. Run this migration script again")
        return False
    
    # Create the database if it doesn't exist
    db_exists = run_command(f"psql -U {os.environ['DB_USER']} -h {os.environ['DB_HOST']} -p {os.environ['DB_PORT']} -lqt | findstr {os.environ['DB_NAME']}", "Checking if database exists")
    
    if not db_exists:
        print(f"Database '{os.environ['DB_NAME']}' does not exist. Creating it now...")
        if not run_command(f"psql -U {os.environ['DB_USER']} -h {os.environ['DB_HOST']} -p {os.environ['DB_PORT']} -c \"CREATE DATABASE {os.environ['DB_NAME']} WITH ENCODING 'UTF8';\" postgres", "Creating PostgreSQL database"):
            print(f"ERROR: Failed to create database '{os.environ['DB_NAME']}'. Please check PostgreSQL configuration.")
            print("You may need to:")
            print("1. Ensure PostgreSQL service is running")
            print("2. Verify the postgres user password")
            print("3. Run the setup_postgres.bat script")
            return False
    
    # Unset SQLite environment variable
    if "USE_SQLITE" in os.environ:
        del os.environ["USE_SQLITE"]
    
    # Check PostgreSQL connection
    print("Checking PostgreSQL connection...")
    if not run_command("python manage.py check", "Checking Django project configuration"):
        print("Django project check failed. Please ensure PostgreSQL is properly configured.")
        return False
    
    # Step 4: Create PostgreSQL database schema
    print("\n=== Step 4: Creating PostgreSQL database schema ===")
    
    if not run_command("python manage.py migrate", "Creating database schema"):
        print("Failed to create database schema. Please check PostgreSQL configuration.")
        return False
    
    # Step 5: Load data into PostgreSQL
    print("\n=== Step 5: Loading data into PostgreSQL ===")
    
    if not run_command(f"python manage.py loaddata {os.path.join(fixtures_dir, 'all_data.json')}", 
                     "Loading data into PostgreSQL"):
        print("Failed to load data into PostgreSQL. You may need to fix the fixture file manually.")
        return False
    
    # Step 6: Verify migration
    print("\n=== Step 6: Verifying migration ===")
    if not run_command("python manage.py check", "Final verification"):
        print("Verification failed. Please check the database configuration.")
        return False
    
    print("\n=== Migration completed successfully! ===")
    print("Your data has been migrated from SQLite to PostgreSQL.")
    print(f"A backup of your SQLite database is available at: {backup_path}")
    
    return True

if __name__ == "__main__":
    # Start migration
    print("=== Starting migration from SQLite to PostgreSQL ===")
    
    # Confirm before proceeding
    response = input("This will migrate your data from SQLite to PostgreSQL. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Migration aborted.")
        sys.exit(0)
    
    # Run migration
    success = migrate_to_postgres()
    
    if success:
        sys.exit(0)
    else:
        print("\nMigration encountered errors. Please check the output above.")
        sys.exit(1) 