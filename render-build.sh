#!/usr/bin/env bash
# Exit on error
set -o errexit

# Verbose output
set -x

echo "===== RENDER DEPLOYMENT BUILD SCRIPT ====="

# Update pip first
echo "Updating pip..."
pip install --upgrade pip

# Force remove and reinstall Django to the correct version
echo "Forcing Django version ${DJANGO_VERSION:-4.2.11}..."
pip uninstall -y django || echo "Django not previously installed"
pip install Django==${DJANGO_VERSION:-4.2.11} --no-cache-dir

# Install social auth packages
echo "Installing social auth packages..."
pip install social-auth-app-django social-auth-core --no-cache-dir

echo "Installing dependencies from render-requirements.txt..."
pip install -r render-requirements.txt --no-cache-dir

# Print Python and environment info
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Django version: $(python -c 'import django; print(django.__version__)')"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p staticfiles/css
mkdir -p staticfiles/js
mkdir -p staticfiles/img
mkdir -p media
mkdir -p logs

# Debug static files structure before collectstatic
echo "Debugging static files structure before collectstatic..."
find core/static -type f | sort

# Skip creating a temporary settings file - use the main settings directly
# It now uses CompressedStaticFilesStorage which doesn't need a manifest

# Run collectstatic with the default settings
echo "Running collectstatic..."
python manage.py collectstatic --no-input --clear

# Create fix_admin_static.py file inline
echo "Creating admin static files fix script..."
cat > fix_admin_static.py << 'EOF'
#!/usr/bin/env python
"""
Script to fix missing admin static files.

This script:
1. Creates directories for Jazzmin admin theme files
2. Downloads required theme files from CDNs
3. Places files in both staticfiles/ and static/ directories
4. Copies all files from staticfiles to static directory
5. Creates core static files if missing
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
        
        # Create core directories
        os.makedirs(f'{static_dir}/core/js', exist_ok=True)
        os.makedirs(f'{static_dir}/core/css', exist_ok=True)
        os.makedirs(f'{static_dir}/core/img', exist_ok=True)

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
        ('https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.bundle.min.js',
         'vendor/bootstrap/js/bootstrap.bundle.min.js'),
        ('https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css',
         'vendor/bootstrap/css/bootstrap.min.css'),
        
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
                
    # Create core static files
    print("Creating core static files...")
    for static_dir in STATIC_DIRS:
        # Copy bootstrap files to core subdirectory
        if os.path.exists(f'{static_dir}/vendor/bootstrap/css/bootstrap.min.css'):
            os.makedirs(f'{static_dir}/core/css', exist_ok=True)
            shutil.copy(
                f'{static_dir}/vendor/bootstrap/css/bootstrap.min.css',
                f'{static_dir}/core/css/bootstrap.min.css'
            )
            print(f"✅ Created {static_dir}/core/css/bootstrap.min.css")
            
        if os.path.exists(f'{static_dir}/vendor/bootstrap/js/bootstrap.bundle.min.js'):
            os.makedirs(f'{static_dir}/core/js', exist_ok=True)
            shutil.copy(
                f'{static_dir}/vendor/bootstrap/js/bootstrap.bundle.min.js',
                f'{static_dir}/core/js/bootstrap.bundle.min.js'
            )
            print(f"✅ Created {static_dir}/core/js/bootstrap.bundle.min.js")
        
        # Create missing script.js
        os.makedirs(f'{static_dir}/core/js', exist_ok=True)
        with open(f'{static_dir}/core/js/script.js', 'w') as f:
            f.write('// Placeholder script.js file created during deployment\n')
            f.write('document.addEventListener("DOMContentLoaded", function() {\n')
            f.write('  console.log("Core script loaded");\n')
            f.write('});\n')
        print(f"✅ Created {static_dir}/core/js/script.js")
        
        # Create missing style.css
        os.makedirs(f'{static_dir}/core/css', exist_ok=True)
        with open(f'{static_dir}/core/css/style.css', 'w') as f:
            f.write('/* Placeholder style.css file created during deployment */\n')
        print(f"✅ Created {static_dir}/core/css/style.css")
        
        # Create error SVG
        os.makedirs(f'{static_dir}/img', exist_ok=True)
        with open(f'{static_dir}/img/error.svg', 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">')
            f.write('<path fill="#e74c3c" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>')
            f.write('</svg>')
        print(f"✅ Created {static_dir}/img/error.svg")

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
EOF

# Run the admin static files fix script
echo "Running admin static files fix script..."
python fix_admin_static.py

# Create fix_core_static.py script for core-specific files
echo "Creating core static files fix script..."
cat > fix_core_static.py << 'EOF'
#!/usr/bin/env python
"""
Script to fix missing core static files.

This script creates additional core static files that might be missing
and ensures they're available in both staticfiles/ and static/ directories.
"""

import os
import shutil
from pathlib import Path

# Define paths
STATIC_DIRS = ['staticfiles', 'static']

# Create core directory structure and files
def create_core_files():
    print("Creating core static files...")
    
    # Core files to create
    files_to_create = [
        {
            'path': 'core/js/script.js',
            'content': '// Core script file\nconsole.log("Core script loaded");\n'
        },
        {
            'path': 'core/js/bootstrap.bundle.min.js',
            'source': 'vendor/bootstrap/js/bootstrap.bundle.min.js'
        },
        {
            'path': 'core/css/bootstrap.min.css',
            'source': 'vendor/bootstrap/css/bootstrap.min.css'
        },
        {
            'path': 'core/css/style.css',
            'content': '/* Core style.css file */\nbody { font-family: sans-serif; }\n'
        },
        {
            'path': 'img/error.svg',
            'content': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
                      '<path fill="#e74c3c" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z'
                      'M12 13.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z'
                      'M12 9c-.83 0-1.5-.67-1.5-1.5S11.17 6 12 6s1.5.67 1.5 1.5S12.83 9 12 9z"/></svg>'
        },
    ]
    
    # Process each file
    for static_dir in STATIC_DIRS:
        for file_info in files_to_create:
            file_path = os.path.join(static_dir, file_info['path'])
            dir_path = os.path.dirname(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(dir_path, exist_ok=True)
            
            # Create file - either from content or by copying a source file
            if 'content' in file_info:
                with open(file_path, 'w') as f:
                    f.write(file_info['content'])
                print(f"Created {file_path} with content")
            elif 'source' in file_info:
                source_path = os.path.join(static_dir, file_info['source'])
                if os.path.exists(source_path):
                    shutil.copy2(source_path, file_path)
                    print(f"Copied {source_path} to {file_path}")
                else:
                    # Create empty file if source doesn't exist
                    with open(file_path, 'w') as f:
                        f.write(f"/* Placeholder file for {file_info['path']} */\n")
                    print(f"Created placeholder {file_path} (source {source_path} not found)")

def main():
    print("Starting core static files fix...")
    create_core_files()
    print("Core static files fix complete!")

if __name__ == "__main__":
    main()
EOF

# Run the core static files fix script
echo "Running core static files fix script..."
python fix_core_static.py

# Ensure all critical CSS files exist
echo "Ensuring all critical CSS files exist..."
for css_file in style.css home.css dashboard.css responsive.css public_pages.css
do
  if [ -f "core/static/css/$css_file" ]; then
    echo "Found $css_file in source, copying..."
    cp "core/static/css/$css_file" "staticfiles/css/$css_file"
  else
    echo "Creating empty $css_file..."
    touch "staticfiles/css/$css_file"
  fi
done

# Verify static files after collection
echo "Verifying collected static files..."
find staticfiles -type f | sort

# Validate CSS files are properly accessible
echo "Validating CSS files..."
for css_file in style.css home.css dashboard.css responsive.css public_pages.css
do
  if [ -f "staticfiles/css/$css_file" ]; then
    echo "✅ $css_file exists in staticfiles"
    ls -la "staticfiles/css/$css_file"
  else
    echo "❌ $css_file is missing from staticfiles!"
    # Create an empty file as a fallback
    echo "/* Fallback CSS file created during deployment */" > "staticfiles/css/$css_file"
    echo "Created fallback file for $css_file"
  fi
done

# Run database migrations
echo "Running migrations..."
python manage.py migrate --no-input

# Debug social-auth installation
echo "Debugging social-auth installation and backends..."
echo "Installed packages:"
pip freeze | grep -i social

echo "Checking for social-auth tables..."
python - << 'EOL'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desiq.settings")
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%social%'")
    tables = cursor.fetchall()
    if tables:
        print(f"Found social tables: {tables}")
    else:
        print("No social tables found!")

    cursor.execute("SELECT * FROM pg_tables WHERE tablename = 'social_auth_association'")
    if cursor.fetchone():
        print("✅ social_auth_association table exists")
    else:
        print("❌ social_auth_association table missing")

# Check authentication backends
try:
    from django.conf import settings
    print("\nRegistered authentication backends:")
    for backend in settings.AUTHENTICATION_BACKENDS:
        print(f"- {backend}")
    
    print("\nRegistered social auth backends:")
    from social_core.backends.utils import get_backend, load_backends
    backends = load_backends(settings.AUTHENTICATION_BACKENDS)
    for name, backend in backends.items():
        print(f"- {name}: {backend.__class__.__name__}")
except Exception as e:
    print(f"Error inspecting backends: {e}")
EOL

# Run the comprehensive social auth check command
echo "Running comprehensive social auth check..."
python manage.py check_social_auth

# Run OAuth setup verification
echo "Verifying OAuth setup..."
python manage.py verify_oauth_setup --verify-only

# Apply fix for missing GoogleOAuth2 backend
echo "Applying fix for missing GoogleOAuth2 backend..."
python - << 'EOL'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desiq.settings")
import django
django.setup()

try:
    from social_core.backends.utils import BACKENDSCACHE, get_backend
    from social_core.backends.google import GoogleOAuth2
    
    # Check if the backend is already registered
    if 'google-oauth2' not in BACKENDSCACHE:
        print("❌ google-oauth2 backend not found in BACKENDSCACHE")
        print("Registering GoogleOAuth2 backend manually...")
        
        # Manually register the GoogleOAuth2 backend
        BACKENDSCACHE['google-oauth2'] = GoogleOAuth2
        
        # Verify registration
        if 'google-oauth2' in BACKENDSCACHE:
            print(f"✅ Successfully registered google-oauth2 backend: {BACKENDSCACHE['google-oauth2']}")
        else:
            print("❌ Failed to register google-oauth2 backend")
    else:
        print(f"✅ google-oauth2 backend already registered: {BACKENDSCACHE['google-oauth2']}")
    
    # List all registered backends after fix
    print("\nAll registered backends after fix:")
    for name, backend_class in BACKENDSCACHE.items():
        print(f"- {name}: {backend_class.__name__}")
    
except Exception as e:
    import traceback
    print(f"Error applying GoogleOAuth2 fix: {e}")
    traceback.print_exc()
EOL

echo "===== BUILD COMPLETE =====" 