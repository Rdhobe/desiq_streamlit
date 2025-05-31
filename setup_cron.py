#!/usr/bin/env python
"""
Script to set up a cron job for daily challenge generation.
This should be run once to set up the cron job.
"""

import os
import sys
from crontab import CronTab

def setup_cron():
    """Set up a cron job to run the generate_daily_challenges management command at midnight every day."""
    try:
        # Get the current user's crontab
        cron = CronTab(user=True)
        
        # Get the absolute path to the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get the absolute path to the Python executable
        python_exe = sys.executable
        
        # Create the command to run
        command = f"cd {project_dir} && {python_exe} manage.py generate_daily_challenges"
        
        # Check if the job already exists
        for job in cron:
            if command in str(job):
                print("Cron job already exists. Skipping.")
                return
        
        # Create a new job that runs at midnight every day
        job = cron.new(command=command)
        job.setall('0 0 * * *')  # Run at midnight every day
        
        # Write the changes to the crontab
        cron.write()
        
        print("Cron job set up successfully. Daily challenges will be generated at midnight every day.")
    
    except Exception as e:
        print(f"Error setting up cron job: {str(e)}")
        print("You may need to manually set up the cron job:")
        print(f"0 0 * * * cd {project_dir} && {python_exe} manage.py generate_daily_challenges")

if __name__ == "__main__":
    setup_cron() 