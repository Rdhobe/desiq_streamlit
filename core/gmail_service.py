import base64
import json
import os
import logging
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

# Configure logging
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """Get a Gmail API service instance."""
    creds = None
    # Token file stores the user's access and refresh tokens
    token_path = os.environ.get('GMAIL_TOKEN_PATH', 'gmail_token.json')
    credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH', 'credentials.json')
    
    # Check if we're running on Render or similar production environment
    is_production = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)
    
    if is_production:
        # In production, we use pre-authorized credentials rather than interactive flow
        logger.info("Running in production mode - using pre-authorized credentials")
        try:
            # Check if we have credentials as environment variables
            if os.environ.get('GMAIL_TOKEN'):
                # Use token from environment variable
                creds = Credentials.from_authorized_user_info(
                    json.loads(os.environ.get('GMAIL_TOKEN')), SCOPES)
                logger.info("Using credentials from environment variable")
            elif os.path.exists(token_path):
                # Use token from file
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(token_path).read()), SCOPES)
                logger.info(f"Using credentials from token file: {token_path}")
            else:
                logger.error("No credentials found for production environment")
                raise Exception("Gmail API credentials not found in production environment")
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in Gmail token")
            raise Exception("Gmail token is not valid JSON format")
        except Exception as e:
            logger.error(f"Error loading Gmail API credentials in production: {e}")
            raise
    else:
        # Development mode - use interactive flow if needed
        logger.info("Running in development mode - interactive flow enabled")
        
        # Check if token.json exists
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(token_path).read()), SCOPES)
                logger.info(f"Loaded existing credentials from {token_path}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON format in token file: {token_path}")
                creds = None
            except Exception as e:
                logger.error(f"Error loading token file: {e}")
                creds = None
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired token")
                    creds.refresh(Request())
                except RefreshError as e:
                    logger.error(f"Token refresh failed (invalid_grant): {e}")
                    logger.info("This usually happens when access was revoked or you used a different account")
                    logger.info("Starting new authorization flow...")
                    creds = None
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                try:
                    logger.info("Starting OAuth flow")
                    if not os.path.exists(credentials_path):
                        raise Exception(f"Credentials file not found: {credentials_path}")
                    
                    logger.info(f"Using credentials from: {credentials_path}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES)
                    # Use port 8080 for consistent redirect URI
                    creds = flow.run_local_server(port=8080)
                    
                    # Save token to environment for potential future deployment
                    print("\n=== TOKEN FOR DEPLOYMENT ===")
                    print("Add this to your Render environment variables as GMAIL_TOKEN:")
                    print(json.dumps(json.loads(creds.to_json())))
                    print("===============================\n")
                    
                except Exception as e:
                    logger.error(f"Error in OAuth flow: {e}")
                    if "redirect_uri_mismatch" in str(e).lower():
                        logger.error("REDIRECT URI MISMATCH ERROR!")
                        logger.error("Please make sure you've added exactly http://localhost:8080/ to your")
                        logger.error("Google Cloud Console project under Credentials > OAuth Client ID.")
                    raise
            
            # Save the credentials for the next run
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved new credentials to {token_path}")
            except Exception as e:
                logger.error(f"Error saving credentials: {e}")
    
    # Return Gmail API service
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as e:
        status = getattr(e, 'status', None)
        reason = getattr(e, 'reason', str(e))
        logger.error(f"Google API HTTP Error {status}: {reason}")
        if status == 403:
            logger.error("Access forbidden - check if Gmail API is enabled in your Google Cloud Console")
        raise
    except Exception as e:
        logger.error(f"Error building Gmail service: {e}")
        raise

def send_email(to, subject, body, from_email=None):
    """Send an email using the Gmail API.
    
    Args:
        to: Email address of the receiver
        subject: Subject of the email
        body: Body text of the email (HTML)
        from_email: Sender's email address
    
    Returns:
        The sent message object
    """
    try:
        service = get_gmail_service()
        
        # Create a message
        message = MIMEText(body, 'html')
        message['to'] = to
        message['subject'] = subject
        if from_email:
            message['from'] = from_email
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the message
        message = service.users().messages().send(
            userId='me', body={'raw': raw_message}).execute()
        
        logger.info(f"Email sent successfully to {to} (Message ID: {message.get('id')})")
        return message
    except HttpError as e:
        status = getattr(e, 'status', None)
        reason = getattr(e, 'reason', str(e))
        logger.error(f"Gmail API Error {status}: {reason}")
        print(f"Gmail API Error: {reason}")
        return None
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        print(f"An error occurred: {e}")
        return None

def test_email(to_email=None):
    """Send a test email to verify Gmail API configuration."""
    if not to_email:
        print("No recipient email provided. Please specify an email address.")
        return False
    
    # HTML email content for testing
    email_body = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 5px; }
            .header { background-color: #f8f9fa; padding: 10px; text-align: center; }
            .content { padding: 20px; }
            .footer { font-size: 12px; text-align: center; margin-top: 20px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>DesiQ Gmail API Test</h2>
            </div>
            <div class="content">
                <p>This is a test email from DesiQ to verify that Gmail API integration is working correctly.</p>
                <p>If you're receiving this email, it means your Gmail API setup is complete and working properly!</p>
            </div>
            <div class="footer">
                <p>This is an automated message - please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        print(f"Sending test email to {to_email}...")
        result = send_email(
            to=to_email,
            subject="DesiQ Gmail API Test",
            body=email_body
        )
        
        if result:
            print("✓ Test email sent successfully!")
            print(f"Message ID: {result.get('id', 'unknown')}")
            return True
        else:
            print("✗ Failed to send test email.")
            return False
    except Exception as e:
        print(f"✗ Error sending test email: {e}")
        return False

# For testing the service
if __name__ == "__main__":
    import json
    import sys
    
    print("Gmail API Service Test")
    print("=====================")
    
    # Check if email address was provided as command line argument
    if len(sys.argv) > 1:
        test_email(sys.argv[1])
    else:
        email = input("Enter an email address to receive the test message: ")
        if email:
            test_email(email)
        else:
            print("No email provided. Test canceled.") 