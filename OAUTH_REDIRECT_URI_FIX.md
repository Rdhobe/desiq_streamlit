# Fixing OAuth Redirect URI Mismatch Errors

If you're encountering "redirect_uri_mismatch" errors while setting up the Gmail API, this guide will help you resolve the issue.

## Understanding the Problem

The OAuth 2.0 flow used by the Gmail API requires an exact match between:
1. The redirect URI configured in your Google Cloud Console project
2. The redirect URI used by the application during the authentication flow

Our application uses `http://localhost:8080/` as the redirect URI, so this exact URI must be added to your OAuth client settings.

## Step-by-Step Fix

1. **Go to Google Cloud Console**
   - Visit [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Select your project

2. **Navigate to OAuth Client Settings**
   - In the left sidebar, click on "APIs & Services" → "Credentials"
   - Find your OAuth client ID in the list (it should be a Desktop client type)
   - Click on the pencil icon to edit it

3. **Add the Exact Redirect URI**
   - Under "Authorized redirect URIs", click "ADD URI"
   - Enter **exactly**: `http://localhost:8080/`
   - Make sure to include the trailing slash (/)
   - Click "SAVE"

   ![Redirect URI Configuration](https://storage.googleapis.com/support-kms-prod/zyGWZMpfVuu7cIaNwfWMvJjvLuHLEJYSAZUx)
   (Example image - your screen may look slightly different)

4. **Additional URI to Add**
   - You can also add `http://127.0.0.1:8080/` as a backup

5. **Wait for Changes to Propagate**
   - It can take a few minutes for the changes to take effect
   - You may need to refresh your credentials.json file (download a new one)

6. **Run the Setup Script Again**
   ```
   python setup_gmail_api.py
   ```

## Verifying the Fix

After making these changes:

1. Delete your existing `gmail_token.json` file (if any)
2. Run the setup script again
3. A browser should open to Google's OAuth consent screen
4. After granting permission, you should be redirected back to your application
5. The setup should complete successfully

## Common Mistakes to Avoid

- **Missing trailing slash**: Make sure the URI ends with `/` (http://localhost:8080/)
- **Using the wrong port**: Our application is hardcoded to use port 8080
- **HTTP vs HTTPS**: Make sure you're using `http://` not `https://`
- **Extra spaces**: Ensure there are no spaces before or after the URI

## Still Having Issues?

1. **Check error messages**: The exact error message may provide additional clues
2. **Download fresh credentials**: Get a new credentials.json file from Google Cloud Console
3. **Check OAuth consent screen**: Make sure you've added yourself as a test user
4. **Review API enabling**: Confirm that the Gmail API is enabled for your project

If you continue to have issues, please contact the development team with:
- Screenshots of your OAuth client settings
- The exact error message you're receiving
- The steps you've taken to troubleshoot 