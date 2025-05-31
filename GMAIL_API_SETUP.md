# Gmail API Setup for DesiQ

This document explains how to set up the Gmail API for sending emails from your DesiQ application.

## Why Use Gmail API?

The Gmail API offers several advantages over standard SMTP:
- More secure (uses OAuth2 instead of storing passwords)
- Higher sending limits
- Better deliverability
- HTML email support
- Sent emails appear in your Gmail "Sent" folder

## Prerequisites

1. A Google account
2. Python 3.6 or higher
3. The required packages (included in requirements.txt)

## Setup Options

### Option 1: Quick Setup for Forgot Password Feature (Recommended)

We've created a simple setup script specifically for the forgot password feature:

1. Run the setup batch file:
   ```
   setup_forgot_password_gmail.bat
   ```

2. The script will:
   - Check if you have the required Google API libraries installed
   - Guide you through setting up your credentials
   - Handle authentication with Google
   - Test sending a password reset email
   - Configure your .env file automatically

3. After running the script, your forgot password emails will be sent via Gmail API

### Option 2: Manual Setup Process

If you prefer to set up Gmail API manually, follow these steps:

#### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the Gmail API:
   - In the left sidebar, go to "APIs & Services" > "Library"
   - Search for "Gmail API" and select it
   - Click "Enable"

#### 2. Create OAuth Client ID Credentials

1. In the Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" and select "OAuth client ID"
3. For Application type, select "Desktop app"
4. Name your client ID (e.g., "DesiQ Email Client")
5. Click "Create"

#### 3. Configure Redirect URIs (Critical Step)

The OAuth flow requires exact matching of redirect URIs:

1. In the Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click on your OAuth client ID to edit it
3. Under "Authorized redirect URIs", add these exact URIs:
   ```
   http://localhost:8080/
   http://127.0.0.1:8080/
   ```
   Note: Include the trailing slash. The URI must match exactly.
4. Click "Save"

5. In the OAuth consent screen:
   - Add yourself as a test user 
   - Fill in the required app information

6. Download the JSON file by clicking the download icon
7. Save this file as `credentials.json` in your DesiQ project root directory

#### 4. Run the Setup Script

We've provided a setup script to help you configure Gmail API access:

On Windows:
```
setup_gmail_api.bat
```

On Mac/Linux:
```
python3 setup_gmail_api.py
```

When you run this script:
1. A browser window will open asking you to sign in to your Google account
2. Grant the requested permissions (send email as you)
3. The script will create a `gmail_token.json` file with your access token
4. You'll see instructions for updating your `.env` file

#### 5. Update Your Environment Variables

Add these lines to your `.env` file:

```
USE_GMAIL_API=True
GMAIL_TOKEN_PATH=gmail_token.json
GMAIL_CREDENTIALS_PATH=credentials.json
```

## Deployment Configuration

### For Local Development

Your local setup should work without further configuration once the `.env` file is updated.

### For Render Deployment

1. During the local setup process, the script will print a token JSON string
2. Copy this entire JSON string
3. In your Render dashboard:
   - Go to your web service
   - Navigate to "Environment"
   - Add these environment variables:
     - `USE_GMAIL_API`: `True`
     - `GMAIL_TOKEN`: [paste the entire JSON string here]
     - `RENDER`: `True`

## Testing Password Reset Emails

To test that password reset emails are working properly:

1. Run our test script:
   ```
   python test_password_reset_email.py your.email@example.com
   ```
   
2. You should receive a test password reset email at the address you provided

3. You can also test the entire forgot password flow by:
   - Go to the login page
   - Click "Forgot password"
   - Enter your email address
   - Check your email for the reset link

## Troubleshooting

### Common Redirect URI Issues

If you see "redirect_uri_mismatch" errors:

1. Double-check that you've added **exactly** `http://localhost:8080/` (with the trailing slash) to your OAuth client's redirect URIs
2. Make sure you're using the correct OAuth client credentials - download a fresh `credentials.json` if needed
3. Our script uses port 8080 consistently - never try to change this port as it will cause redirect URI mismatches

### Token Expired or Invalid

If you see token errors, simply delete the `gmail_token.json` file and run the setup script again.

### "Access Not Configured" Errors

Make sure:
- The Gmail API is enabled in your Google Cloud Project
- You've waited a few minutes after enabling the API (it can take time to propagate)

### "Invalid Grant" Errors

These typically happen when:
- You used a different Google account than expected
- You've revoked access for the app
- The refresh token has expired or been invalidated

Solution: Delete `gmail_token.json` and restart the authorization flow.

### Permission Errors

If you get "Permission denied" errors when saving token files, run the script with appropriate permissions or save the files to a directory where you have write access.

## Security Notes

- Keep your `credentials.json` and `gmail_token.json` files secure - they grant access to send emails as you
- In production, store these files outside your web root and update the paths in your environment variables
- The token includes a refresh token that will be used automatically when the access token expires 