import os
import sys
import subprocess
import platform

def run_streamlit():
    """
    Run the streamlit app with the appropriate environment setup
    """
    print("Starting DesiQ Streamlit Dashboard...")
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("Streamlit is already installed.")
    except ImportError:
        print("Installing Streamlit and dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "streamlit_requirements.txt"])
        print("Streamlit and dependencies installed successfully.")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH to include the current directory
    env = os.environ.copy()
    python_path = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{python_path}"
    
    # Run the streamlit app
    cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--browser.serverAddress", "localhost", "--server.port", "8501"]
    
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
    run_streamlit() 