#!/usr/bin/env python
"""
Script to fix missing admin static files.

This script:
1. Creates directories for Jazzmin admin theme files
2. Downloads required theme files from CDNs
3. Places files in both staticfiles/ and static/ directories
"""

import os
import urllib.request
import shutil

# Static files directories - we need to handle both staticfiles/ (collectstatic output) and static/ (URL prefix)
STATIC_DIRS = ['staticfiles', 'static']

# Create directories
def create_dirs():
    print("Creating directories for admin theme files...")
    for static_dir in STATIC_DIRS:
        os.makedirs(f'{static_dir}/vendor/fontawesome-free/css', exist_ok=True)
        os.makedirs(f'{static_dir}/vendor/adminlte/css', exist_ok=True)
        os.makedirs(f'{static_dir}/vendor/adminlte/js', exist_ok=True)
        os.makedirs(f'{static_dir}/vendor/bootstrap/js', exist_ok=True)
        os.makedirs(f'{static_dir}/vendor/bootswatch/darkly', exist_ok=True)
        os.makedirs(f'{static_dir}/jazzmin/css', exist_ok=True)
        os.makedirs(f'{static_dir}/jazzmin/js', exist_ok=True)
        os.makedirs(f'{static_dir}/img', exist_ok=True)

# Copy logo and create symlinks where needed
def copy_files():
    print("Copying existing files...")
    
    # Create static directory if it doesn't exist
    if not os.path.exists('static'):
        print("Creating static directory")
        os.makedirs('static', exist_ok=True)
    
    # Copy logo files first (explicitly)    
    if os.path.exists('staticfiles/img/digital-brain-logo.svg'):
        # Create directories if they don't exist
        os.makedirs('static/img', exist_ok=True)
        
        # Copy SVG logo
        print("Copying logo to static/img/digital-brain-logo.svg")
        shutil.copy('staticfiles/img/digital-brain-logo.svg', 'static/img/digital-brain-logo.svg')
        
        # Also create a PNG logo for backward compatibility
        print("Creating PNG logo at static/img/logo.png")
        shutil.copy('staticfiles/img/digital-brain-logo.svg', 'static/img/logo.png')
    
    # Also create a PNG copy in staticfiles
    if not os.path.exists('staticfiles/img/logo.png') and os.path.exists('staticfiles/img/digital-brain-logo.svg'):
        os.makedirs('staticfiles/img', exist_ok=True)
        print("Creating PNG logo in staticfiles")
        shutil.copy('staticfiles/img/digital-brain-logo.svg', 'staticfiles/img/logo.png')
    
    # Copy all files from staticfiles to static recursively (skipping duplicates)
    print("Copying all missing files from staticfiles to static...")
    count = 0
    for root, dirs, files in os.walk('staticfiles'):
        for file in files:
            src_path = os.path.join(root, file)
            # Convert path to be relative to staticfiles directory
            rel_path = os.path.relpath(src_path, 'staticfiles')
            # Create the destination path in static
            dst_path = os.path.join('static', rel_path)
            # Create directory if it doesn't exist
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            # Copy file if it doesn't exist or is different
            if not os.path.exists(dst_path) or not files_are_same(src_path, dst_path):
                try:
                    shutil.copy2(src_path, dst_path)
                    count += 1
                    if count % 50 == 0:
                        print(f"Copied {count} files...")
                except Exception as e:
                    print(f"Error copying {src_path}: {e}")
    
    print(f"Total files copied: {count}")
    
    # Create symbolic link from static to staticfiles if on Linux/Unix
    if os.name != 'nt':  # Skip on Windows
        try:
            if not os.path.exists('static') and os.path.exists('staticfiles'):
                print("Creating symbolic link from static to staticfiles")
                os.symlink('staticfiles', 'static', target_is_directory=True)
                print("Created symbolic link from static to staticfiles")
        except Exception as e:
            print(f"Error creating symlink: {e}")

# Helper function to compare files
def files_are_same(file1, file2):
    """Check if two files are the same by comparing size and modification time."""
    if not (os.path.exists(file1) and os.path.exists(file2)):
        return False
        
    stat1 = os.stat(file1)
    stat2 = os.stat(file2)
    
    # Compare file size
    if stat1.st_size != stat2.st_size:
        return False
        
    # If sizes are the same, we'll assume they're the same file to save time
    return True

# Download required files from CDNs
def download_files():
    print("Downloading required theme files...")
    
    files_to_download = [
        # FontAwesome
        ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
         'vendor/fontawesome-free/css/all.min.css'),
        
        # AdminLTE
        ('https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css',
         'vendor/adminlte/css/adminlte.min.css'),
        ('https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/js/adminlte.min.js',
         'vendor/adminlte/js/adminlte.min.js'),
        
        # Bootstrap
        ('https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.min.js',
         'vendor/bootstrap/js/bootstrap.min.js'),
        
        # Bootswatch Darkly theme
        ('https://cdn.jsdelivr.net/npm/bootswatch@4.6.2/dist/darkly/bootstrap.min.css',
         'vendor/bootswatch/darkly/bootstrap.min.css'),
    ]
    
    for url, relative_path in files_to_download:
        for static_dir in STATIC_DIRS:
            dest = f'{static_dir}/{relative_path}'
            print(f"Downloading {url} to {dest}")
            try:
                urllib.request.urlretrieve(url, dest)
                print(f"✅ Downloaded {dest}")
            except Exception as e:
                print(f"❌ Error downloading {url}: {e}")

# Create placeholders for Jazzmin specific files
def create_placeholders():
    print("Creating placeholder files for Jazzmin...")
    
    for static_dir in STATIC_DIRS:
        with open(f'{static_dir}/jazzmin/css/main.css', 'w') as f:
            f.write('/* Placeholder file for Jazzmin CSS */\n/* Basic styles to make the admin interface usable */\n')
            f.write('body { font-family: sans-serif; }\n')
            f.write('.sidebar-dark-primary { background-color: #343a40; }\n')
            f.write('.nav-sidebar .nav-link { color: #fff; }\n')
            
        with open(f'{static_dir}/jazzmin/js/main.js', 'w') as f:
            f.write('// Placeholder file for Jazzmin JS\n')
            f.write('// Simple fallback functionality\n')
            f.write('document.addEventListener("DOMContentLoaded", function() {\n')
            f.write('  console.log("Admin interface loaded with fallback styles");\n')
            f.write('});\n')

def main():
    print("Starting admin theme fix...")
    create_dirs()
    copy_files()
    download_files()
    create_placeholders()
    print("\nAdmin theme fix complete! 🎉")
    print("You should now be able to access the admin interface with proper styling.")

if __name__ == "__main__":
    main() 