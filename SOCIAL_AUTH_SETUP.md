# Social Authentication Setup for DesiQ

This document explains how to set up and use social authentication (Google and GitHub) with your DesiQ application.

## Benefits of Social Authentication

- **Faster Registration/Login**: Users can register and log in with a single click
- **Reduced Friction**: No need to remember another password
- **Higher Conversion**: Typically results in higher signup/login completion rates
- **Better Security**: Less vulnerable to password-related security issues

## Technical Implementation

We've integrated social authentication using the `social-auth-app-django` package with the following components:

1. **Authentication Backends**: Added GitHub and Google OAuth2 backend configurations
2. **URL Routing**: Configured social auth URLs under `/social-auth/`
3. **UI Integration**: Added social login buttons to login and registration pages
4. **Environment Settings**: Set up configuration for OAuth credentials via environment variables

## Setup Instructions

### Prerequisites

1. Install required packages (already included in requirements.txt):
   ```
   pip install social-auth-app-django
   ```

2. Database migrations (run these if you haven't already):
   ```
   python manage.py migrate
   ```

### Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the Application type
6. Add a name (e.g., "DesiQ Web Login")
7. Under "Authorized JavaScript origins" add:
   ```
   http://localhost:8000
   https://your-production-domain.com
   ```
8. Under "Authorized redirect URIs" add:
   ```
   http://localhost:8000/social-auth/complete/google-oauth2/
   https://your-production-domain.com/social-auth/complete/google-oauth2/
   ```
9. Click "Create"
10. Note your Client ID and Client Secret
11. Add these credentials to your `.env` file:
   ```
   GOOGLE_OAUTH2_KEY=your_client_id
   GOOGLE_OAUTH2_SECRET=your_client_secret
   ```

### GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the application details:
   - Application name: DesiQ
   - Homepage URL: http://localhost:8000/ (or your production URL)
   - Authorization callback URL: http://localhost:8000/social-auth/complete/github/ (or your production URL equivalent)
4. Click "Register application"
5. Generate a new client secret
6. Add these credentials to your `.env` file:
   ```
   GITHUB_KEY=your_github_client_id
   GITHUB_SECRET=your_github_client_secret
   ```

## Render Deployment Configuration

When deploying to Render, make sure to add the OAuth client IDs and secrets as environment variables:

1. Go to your Render dashboard
2. Select your web service
3. Navigate to the "Environment" tab
4. Add the following environment variables:
   - `GOOGLE_OAUTH2_KEY`: Your Google OAuth2 client ID
   - `GOOGLE_OAUTH2_SECRET`: Your Google OAuth2 client secret
   - `GITHUB_KEY`: Your GitHub OAuth client ID
   - `GITHUB_SECRET`: Your GitHub OAuth client secret

**Important**: Make sure to update the redirect URIs in both Google and GitHub OAuth settings to include your Render production URL.

## How It Works

1. **User Clicks Social Login Button**: The user initiates the OAuth flow by clicking a social login button
2. **Redirection to Provider**: The user is redirected to the identity provider (Google/GitHub)
3. **Authorization**: The user authorizes the application to access their basic profile information
4. **Callback Processing**: The provider redirects back to DesiQ with an authorization code
5. **Authentication/Registration**: DesiQ verifies the code and either logs in the user or creates a new account
6. **Session Creation**: A Django session is created and the user is redirected to the dashboard

## Troubleshooting

### Common Issues

1. **Redirect URI Mismatch**: The most common error is a mismatch between the redirect URI in your OAuth settings and the one used by your application. Make sure they match exactly.

2. **Missing Credentials**: Check that you've correctly set the OAuth client ID and secret in your environment variables.

3. **User Already Exists**: If a user tries to log in with a social account but already has a local account with the same email, they might see an error. Consider implementing account linking functionality if this is a common issue.

4. **Provider-Specific Issues**:
   - Google: Ensure the OAuth consent screen is configured correctly
   - GitHub: Make sure you've requested the correct scopes (user:email)

## Additional Resources

- [Social Auth Django Documentation](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2/web-server)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps) 