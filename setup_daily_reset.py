import os
import sys
import subprocess
from datetime import datetime, timedelta

def setup_windows_task():
    """
    Set up a Windows scheduled task to run the reset_daily_limits command at midnight
    """
    print("Setting up Windows scheduled task to reset daily limits at midnight...")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to python executable
    python_exe = sys.executable
    
    # Command to run
    command = f'"{python_exe}" "{current_dir}/manage.py" reset_daily_limits'
    
    # Create a batch file to run the command
    batch_file = os.path.join(current_dir, "reset_daily_limits.bat")
    with open(batch_file, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'cd /d "{current_dir}"\n')
        f.write(f'{command}\n')
    
    # Task name
    task_name = "DesiqDailyLimitsReset"
    
    # Delete existing task if it exists
    subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], 
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Create the task to run at midnight every day
    result = subprocess.run([
        "schtasks", "/create", "/tn", task_name,
        "/tr", batch_file,
        "/sc", "daily",
        "/st", "00:00"
    ])
    
    if result.returncode == 0:
        print("Task scheduled successfully!")
        print(f"The daily limits will be reset at midnight.")
    else:
        print("Failed to schedule task. You may need to run this script as administrator.")

if __name__ == "__main__":
    if os.name == "nt":  # Windows
        setup_windows_task()
    else:
        print("This script is for Windows only. For Linux/Mac, use the django-crontab setup.")
        print("Run: python manage.py crontab add") 