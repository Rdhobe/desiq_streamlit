#!/usr/bin/env python
"""
Gmail API Setup for Password Reset Emails

This script:
1. Helps configure Gmail API for password reset emails
2. Creates/updates the necessary credentials
3. Tests sending a password reset email
4. Updates the relevant Django settings
"""
import os
import sys
import json
import django
from pathlib import Path

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desiq.settings")
django.setup()

from django.conf import settings
from core.gmail_service import test_email

def setup_gmail_for_password_reset():
    """Configure Gmail API for password reset emails"""
    print("Password Reset Email Setup using Gmail API")
    print("==========================================")
    
    # Check current configuration
    current_backend = getattr(settings, 'EMAIL_BACKEND', 'unknown')
    gmail_enabled = getattr(settings, 'USE_GMAIL_API', False)
    
    print(f"Current email backend: {current_backend}")
    print(f"Gmail API currently {'enabled' if gmail_enabled else 'disabled'}")
    
    # Get the Gmail API credentials
    creds_path = os.environ.get('GMAIL_CREDENTIALS_PATH', os.path.join(settings.BASE_DIR, 'credentials.json'))
    token_path = os.environ.get('GMAIL_TOKEN_PATH', os.path.join(settings.BASE_DIR, 'gmail_token.json'))
    
    print(f"\nCredentials path: {creds_path}")
    print(f"Token path: {token_path}")
    
    # Check if credentials file exists
    if not os.path.exists(creds_path):
        print("\n❌ Credentials file not found!")
        print("Please download your OAuth credentials JSON file from Google Cloud Console")
        print("and save it as 'credentials.json' in the project root directory.")
        print("\nInstructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select an existing one")
        print("3. Enable the Gmail API")
        print("4. Go to Credentials → Create OAuth client ID → Desktop application")
        print("5. Download the JSON file and rename it to 'credentials.json'")
        print("6. Place it in your project root directory")
        return False
    
    # Run the setup script
    print("\nRunning Gmail API setup...")
    
    # Import the setup function from setup_gmail_api.py
    try:
        sys.path.append(str(settings.BASE_DIR))
        from setup_gmail_api import setup_gmail_api
        setup_success = setup_gmail_api()
        
        if not setup_success:
            print("\n❌ Gmail API setup failed!")
            return False
        
    except Exception as e:
        print(f"\n❌ Error during Gmail API setup: {e}")
        return False
    
    # Update the .env file or settings
    print("\n✓ Gmail API setup completed successfully!")
    print("\nWould you like to test sending a password reset email?")
    test_response = input("Enter 'y' to test, any other key to skip: ").lower()
    
    if test_response == 'y':
        test_email_address = input("\nEnter your email address to receive a test password reset email: ")
        if test_email_address:
            # Temporarily enable Gmail API for the test
            os.environ['USE_GMAIL_API'] = 'True'
            
            try:
                print(f"\nSending test email to {test_email_address}...")
                test_result = test_email(test_email_address)
                
                if test_result:
                    print("\n✓ Password reset email test successful!")
                    print("\nTo enable Gmail API for all password reset emails, add these lines to your .env file:")
                    print("USE_GMAIL_API=True")
                    print(f"GMAIL_TOKEN_PATH={os.path.abspath(token_path)}")
                    print(f"GMAIL_CREDENTIALS_PATH={os.path.abspath(creds_path)}")
                    
                    # Ask if user wants to update .env file automatically
                    update_env = input("\nWould you like to update the .env file automatically? (y/n): ").lower()
                    if update_env == 'y':
                        try:
                            env_path = os.path.join(settings.BASE_DIR, '.env')
                            env_content = ""
                            
                            # Read existing .env content if file exists
                            if os.path.exists(env_path):
                                with open(env_path, 'r') as f:
                                    env_content = f.read()
                            
                            # Check if settings already exist and update them
                            if 'USE_GMAIL_API=' in env_content:
                                env_content = env_content.replace('USE_GMAIL_API=False', 'USE_GMAIL_API=True')
                            else:
                                env_content += "\n# Gmail API settings\nUSE_GMAIL_API=True\n"
                                
                            if 'GMAIL_TOKEN_PATH=' in env_content:
                                # Use regex to replace existing path
                                import re
                                env_content = re.sub(r'GMAIL_TOKEN_PATH=.*', f'GMAIL_TOKEN_PATH={os.path.abspath(token_path)}', env_content)
                            else:
                                env_content += f"GMAIL_TOKEN_PATH={os.path.abspath(token_path)}\n"
                                
                            if 'GMAIL_CREDENTIALS_PATH=' in env_content:
                                # Use regex to replace existing path
                                import re
                                env_content = re.sub(r'GMAIL_CREDENTIALS_PATH=.*', f'GMAIL_CREDENTIALS_PATH={os.path.abspath(creds_path)}', env_content)
                            else:
                                env_content += f"GMAIL_CREDENTIALS_PATH={os.path.abspath(creds_path)}\n"
                            
                            # Write updated content back to .env file
                            with open(env_path, 'w') as f:
                                f.write(env_content)
                                
                            print("\n✓ .env file updated successfully!")
                            print("Gmail API is now configured for password reset emails.")
                            
                        except Exception as e:
                            print(f"\n❌ Error updating .env file: {e}")
                            print("Please update your .env file manually with the values above.")
                            
                else:
                    print("\n❌ Password reset email test failed.")
                    print("Please check the error messages and try again.")
                
            except Exception as e:
                print(f"\n❌ Error testing password reset email: {e}")
        else:
            print("No email address provided. Skipping test.")
    
    print("\nSetup process completed.")
    return True

if __name__ == "__main__":
    setup_gmail_for_password_reset() 