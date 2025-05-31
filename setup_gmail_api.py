#!/usr/bin/env python
"""
Gmail API Setup Script
This script helps with the initial setup of Gmail API access for sending emails.
"""
import os
import json
import sys
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The Gmail API scopes we need
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def setup_gmail_api():
    """Set up Gmail API access and validate credentials."""
    # Check if credentials.json exists
    credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH', 'credentials.json')
    if not os.path.exists(credentials_path):
        print(f"Error: Could not find credentials file at {credentials_path}")
        print("Please download your OAuth client credentials from the Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project (or select an existing one)")
        print("3. Enable the Gmail API")
        print("4. Create OAuth client ID credentials (Desktop app)")
        print("5. In the OAuth consent screen, add yourself as a test user")
        print("6. In the OAuth client ID settings, add these redirect URIs:")
        print("   - http://localhost:8080/")
        print("   - http://127.0.0.1:8080/")
        print("7. Download the JSON file and save it as 'credentials.json'")
        return False
    
    # Get the token file path
    token_path = os.environ.get('GMAIL_TOKEN_PATH', 'gmail_token.json')
    
    # Check if we're running on Render or similar production environment
    is_production = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)
    
    if is_production:
        print("Running in production mode - using pre-authorized credentials")
        from core.gmail_service import get_gmail_service, send_email
        try:
            # Verify production credentials
            service = get_gmail_service()
            profile = service.users().getProfile(userId='me').execute()
            print(f"Successfully connected to Gmail API for: {profile.get('emailAddress')}")
            print("Gmail API is configured correctly for production use.")
            return True
        except Exception as e:
            print(f"Error setting up Gmail API in production: {e}")
            print("\nFor Render deployment, you need to:")
            print("1. Set up Gmail API locally first")
            print("2. Get the token JSON printed during local setup")
            print("3. Add it as an environment variable named GMAIL_TOKEN in your Render dashboard")
            print("4. Set USE_GMAIL_API=True in Render environment variables")
            return False
    
    # Development mode setup
    print("Running in development mode with interactive authentication")
    
    # Try to get credentials
    creds = None
    if os.path.exists(token_path):
        print(f"Found existing token at {token_path}")
        try:
            creds = Credentials.from_authorized_user_info(
                json.loads(open(token_path).read()), SCOPES)
        except Exception as e:
            print(f"Error loading existing token: {e}")
            creds = None
    
    # If credentials don't exist or are invalid, create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            print("Starting OAuth 2.0 authorization flow...")
            print("\nIMPORTANT: Make sure you've added these redirect URIs in Google Cloud Console:")
            print("- http://localhost:8080/")
            print("- http://127.0.0.1:8080/")
            print("\nIf you get a redirect_uri_mismatch error, you need to:")
            print("1. Go to Google Cloud Console > APIs & Services > Credentials")
            print("2. Edit your OAuth client ID")
            print("3. Add exactly 'http://localhost:8080/' to Authorized redirect URIs")
            print("4. Save and try again\n")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                # Always use port 8080 for consistent redirect URI
                creds = flow.run_local_server(port=8080)
                
                # Print token for Render deployment
                print("\n=== TOKEN FOR DEPLOYMENT ===")
                print("Add this to your Render environment variables as GMAIL_TOKEN:")
                print(json.dumps(json.loads(creds.to_json())))
                print("===============================\n")
                
            except Exception as e:
                print(f"Error during authorization: {e}")
                if "redirect_uri_mismatch" in str(e).lower():
                    print("\nREDIRECT URI MISMATCH ERROR DETECTED!")
                    print("This error occurs when the redirect URI used by this app doesn't match")
                    print("what you've configured in Google Cloud Console.")
                    print("\nPlease make sure you've added EXACTLY this redirect URI in your")
                    print("Google Cloud Console project under Credentials > OAuth Client ID:")
                    print("\nhttp://localhost:8080/")
                    print("\nThen run this script again.")
                else:
                    print("Make sure your credentials.json file is valid and you have")
                    print("the correct permissions in your Google Cloud Project.")
                return False
        
        # Save the credentials for future runs
        print(f"Saving new token to {token_path}")
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    # Test the connection
    print("Testing Gmail API connection...")
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        print(f"Successfully connected to Gmail API for: {profile.get('emailAddress')}")
        
        # Add instructions for local environment
        print("\nTo use Gmail API for sending emails, add these to your .env file:")
        print("USE_GMAIL_API=True")
        print(f"GMAIL_TOKEN_PATH={os.path.abspath(token_path)}")
        print(f"GMAIL_CREDENTIALS_PATH={os.path.abspath(credentials_path)}")
        
        # Add instructions for Render deployment
        print("\nFor Render deployment, you'll need to:")
        print("1. Copy the token JSON printed above")
        print("2. Add it as GMAIL_TOKEN environment variable in Render")
        print("3. Set USE_GMAIL_API=True in Render environment variables")
        print("4. Deploy your application")
        
        return True
    except Exception as e:
        print(f"Error testing Gmail API connection: {e}")
        return False

if __name__ == "__main__":
    print("Gmail API Setup Tool")
    print("====================")
    success = setup_gmail_api()
    if success:
        print("\nSetup completed successfully!")
        sys.exit(0)
    else:
        print("\nSetup failed. Please check the error messages and try again.")
        sys.exit(1) 