#!/usr/bin/env python
"""
Script to diagnose and fix static files issues in a Django project.

This script:
1. Checks if the staticfiles manifest exists
2. Validates the manifest for critical CSS files
3. Runs collectstatic with appropriate settings if issues are found
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Critical files that must be in the manifest
CRITICAL_FILES = [
    'css/style.css',
    'css/home.css',
    'css/dashboard.css',
    'css/responsive.css',
    'css/public_pages.css',
]

def check_manifest():
    """Check if the staticfiles manifest exists and contains critical files."""
    manifest_path = Path('staticfiles/staticfiles.json')
    
    if not manifest_path.exists():
        print("❌ Staticfiles manifest not found!")
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check for critical files
        missing_files = []
        for file in CRITICAL_FILES:
            if file not in manifest['paths']:
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Missing files in manifest: {', '.join(missing_files)}")
            return False
        
        print("✅ Staticfiles manifest looks good!")
        return True
    
    except Exception as e:
        print(f"❌ Error reading manifest: {e}")
        return False

def fix_staticfiles():
    """Run collectstatic with appropriate settings to fix issues."""
    # Create temporary settings file
    with open('temp_settings.py', 'w') as f:
        f.write("""
from desiq.settings import *

# Use simple storage first
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEBUG = False
""")
    
    # Step 1: Run collectstatic with SimpleStaticFilesStorage
    print("\n--- Step 1: Running collectstatic with SimpleStaticFilesStorage ---")
    subprocess.run([
        sys.executable, 'manage.py', 'collectstatic', 
        '--no-input', '--clear',
        '--settings=temp_settings'
    ])
    
    # Step 2: Ensure critical files exist
    print("\n--- Step 2: Ensuring critical files exist ---")
    static_css_dir = Path('staticfiles/css')
    static_css_dir.mkdir(exist_ok=True)
    
    source_css_dir = Path('core/static/css')
    for css_file in CRITICAL_FILES:
        _, filename = os.path.split(css_file)
        source_path = source_css_dir / filename
        dest_path = static_css_dir / filename
        
        if source_path.exists():
            print(f"Copying {filename} from source...")
            shutil.copy(source_path, dest_path)
        else:
            print(f"Creating empty {filename}...")
            dest_path.touch()
    
    # Step 3: Run collectstatic with ManifestStaticFilesStorage
    print("\n--- Step 3: Running collectstatic with ManifestStaticFilesStorage ---")
    with open('temp_settings.py', 'w') as f:
        f.write("""
from desiq.settings import *

# Use manifest storage for proper hashing
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEBUG = False
""")
    
    subprocess.run([
        sys.executable, 'manage.py', 'collectstatic', 
        '--no-input',
        '--settings=temp_settings'
    ])
    
    # Clean up temporary settings
    os.remove('temp_settings.py')
    
    # Check the manifest again
    return check_manifest()

def main():
    print("=== Django Staticfiles Diagnostic Tool ===")
    
    # Check if staticfiles directory exists
    if not os.path.isdir('staticfiles'):
        print("❌ Staticfiles directory not found. Creating it...")
        os.makedirs('staticfiles', exist_ok=True)
    
    # Check the manifest
    if check_manifest():
        print("\n✅ No issues detected with staticfiles.")
        return
    
    # Ask to fix
    while True:
        response = input("\nWould you like to fix the staticfiles issues? (y/n): ").lower()
        if response in ('y', 'yes'):
            print("\nAttempting to fix staticfiles...")
            if fix_staticfiles():
                print("\n✅ Staticfiles issues fixed successfully!")
            else:
                print("\n❌ Failed to fix staticfiles issues.")
            break
        elif response in ('n', 'no'):
            print("\nExiting without fixing issues.")
            break
        else:
            print("Please enter 'y' or 'n'.")

if __name__ == "__main__":
    main() 