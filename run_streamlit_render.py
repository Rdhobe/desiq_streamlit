#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
import tempfile
import platform

def setup_environment():
    """Set up environment variables similar to Render deployment"""
    env = os.environ.copy()
    
    # Set critical environment variables similar to render.yaml
    env_vars = {
        "DEBUG": "false",
        "PORT": "8000",
        "DJANGO_SETTINGS_MODULE": "desiq.settings",
        "STATIC_ROOT": os.path.join(os.getcwd(), "staticfiles"),
        "STATIC_URL": "/static/",
        "TEMPLATE_DIRS": "core/templates",
        "DJANGO_VERSION": "4.2.11",
        "WEB_CONCURRENCY": "2",
        "GUNICORN_THREADS": "4",
        "GUNICORN_TIMEOUT": "120",
        "GUNICORN_MAX_REQUESTS": "300",
        "GUNICORN_WORKER_CLASS": "sync",
        "GUNICORN_LOG_LEVEL": "info"
    }
    
    # Update environment with our variables
    for key, value in env_vars.items():
        env[key] = value
        os.environ[key] = value
    
    return env

def prepare_staticfiles():
    """Prepare static files similar to render-build.sh"""
    print("Creating necessary directories...")
    os.makedirs("staticfiles/css", exist_ok=True)
    os.makedirs("staticfiles/js", exist_ok=True)
    os.makedirs("staticfiles/img", exist_ok=True)
    os.makedirs("media", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Run collectstatic if needed
    if not os.path.exists("staticfiles/admin"):
        print("Running collectstatic...")
        subprocess.run([sys.executable, "manage.py", "collectstatic", "--no-input", "--clear"], check=True)
    
    # Fix admin static files if needed
    if os.path.exists("fix_admin_static.py"):
        print("Running admin static files fix...")
        subprocess.run([sys.executable, "fix_admin_static.py"], check=True)

def check_django_setup():
    """Check if Django is properly set up"""
    try:
        # Try running a simple Django command
        result = subprocess.run(
            [sys.executable, "manage.py", "check"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            print("Django project checks passed.")
            return True
        else:
            print(f"Django project check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error checking Django setup: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("Installing required dependencies...")
    
    # First, update pip
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install Django with specific version
    subprocess.run([sys.executable, "-m", "pip", "install", f"Django==4.2.11"], check=True)
    
    # Install from render-requirements.txt if it exists
    if os.path.exists("render-requirements.txt"):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "render-requirements.txt"], check=True)
    
    # Install Streamlit dependencies
    if os.path.exists("streamlit_requirements.txt"):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "streamlit_requirements.txt"], check=True)
    else:
        # Install core Streamlit packages if no requirements file
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit", "pandas", "plotly"], check=True)

def run_migrations():
    """Run Django migrations"""
    print("Running migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate", "--no-input"], check=True)
        print("Migrations completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")

def run_streamlit_with_django():
    """Run Streamlit with Django integration"""
    # Setup environment
    env = setup_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Prepare static files
    prepare_staticfiles()
    
    # Check Django setup
    if not check_django_setup():
        print("WARNING: Django setup check failed. Continuing anyway...")
    
    # Run migrations
    run_migrations()
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH to include the current directory
    python_path = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{python_path}"
    
    # Run the streamlit app
    cmd = [
        sys.executable, 
        "-m", 
        "streamlit", 
        "run", 
        "streamlit_app.py", 
        "--browser.serverAddress", 
        "localhost", 
        "--server.port", 
        "8501"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("Open http://localhost:8501 in your browser if it doesn't open automatically.")
    print("Press Ctrl+C to stop the server.")
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\nStreamlit server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_streamlit_with_django() 