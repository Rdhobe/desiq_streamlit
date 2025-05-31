@echo off
echo DesiQ Gmail API Setup for Password Reset
echo =======================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in your PATH.
    echo Please install Python 3.6 or higher and try again.
    goto :end
)

REM Check which Python version we're using
python --version
echo.

REM Check if required packages are installed
echo Checking required packages...
python -c "import google.oauth2.credentials" > nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required Google API packages...
    python -m pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
) else (
    echo Required Google API packages are already installed.
)
echo.

REM Check for credentials.json
if not exist credentials.json (
    echo WARNING: credentials.json file not found!
    echo This file is required for Gmail API authentication.
    echo.
    echo Please download your OAuth credentials from Google Cloud Console:
    echo 1. Go to https://console.cloud.google.com/
    echo 2. Create a project or select an existing one
    echo 3. Enable the Gmail API
    echo 4. Create OAuth client ID credentials (Desktop app)
    echo 5. Add these redirect URIs to your OAuth client ID:
    echo    - http://localhost:8080/
    echo    - http://127.0.0.1:8080/
    echo 6. Download the JSON file and save it as 'credentials.json' in this directory
    echo.
    choice /C YN /M "Do you want to continue anyway"
    if %errorlevel% equ 2 goto :end
    echo.
)

REM Run the setup script
echo Starting Gmail API setup script...
echo.
python setup_forgot_password_gmail.py

REM Check if setup was successful
if %errorlevel% neq 0 (
    echo.
    echo Setup encountered errors. Please check the messages above.
    echo.
    echo If you're seeing a "redirect_uri_mismatch" error:
    echo 1. Make sure you've added http://localhost:8080/ to your OAuth client's redirect URIs
    echo 2. See OAUTH_REDIRECT_URI_FIX.md for detailed instructions
)

:end
echo.
echo Press any key to exit
pause > nul 