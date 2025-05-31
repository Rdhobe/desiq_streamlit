@echo off
SETLOCAL

echo ===== DesiQ PostgreSQL Setup Helper =====
echo This script will help you set up PostgreSQL for DesiQ

:: Check if PostgreSQL is installed
where psql > nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo PostgreSQL is not installed or not in the system PATH.
    echo.
    echo Please follow these steps:
    echo 1. Download PostgreSQL from https://www.postgresql.org/download/windows/
    echo 2. During installation, note the password you set for the 'postgres' user
    echo 3. Make sure to add PostgreSQL bin directory to your PATH
    echo 4. Run this script again after installation
    pause
    exit /b 1
)

echo PostgreSQL is installed! Proceeding with setup...
echo.

:: Gather database info
set /p DB_NAME=Enter database name [desiq_db]: 
if "%DB_NAME%"=="" set DB_NAME=desiq_db

set /p DB_USER=Enter database user [postgres]: 
if "%DB_USER%"=="" set DB_USER=postgres

set /p DB_PASSWORD=Enter database password: 
if "%DB_PASSWORD%"=="" (
    echo Password cannot be empty
    pause
    exit /b 1
)

set /p DB_HOST=Enter database host [localhost]: 
if "%DB_HOST%"=="" set DB_HOST=localhost

set /p DB_PORT=Enter database port [5432]: 
if "%DB_PORT%"=="" set DB_PORT=5432

echo.
echo Creating .env file with database configuration...

:: Create or update .env file
if exist .env (
    echo Backing up existing .env to .env.bak
    copy .env .env.bak
)

(
echo # Django settings
echo DEBUG=True
echo SECRET_KEY=django-insecure--#00*w5!)fn-!f+_%$+&&3dcjqs6#!04yd(hr=5z+9aq(4w1ki
echo.
echo # PostgreSQL Database Settings
echo DATABASE_URL=postgres://%DB_USER%:%DB_PASSWORD%@%DB_HOST%:%DB_PORT%/%DB_NAME%
echo DB_NAME=%DB_NAME%
echo DB_USER=%DB_USER%
echo DB_PASSWORD=%DB_PASSWORD%
echo DB_HOST=%DB_HOST%
echo DB_PORT=%DB_PORT%
echo.
echo # OpenAI API Key
echo OPENAI_API_KEY=
echo.
echo # Razorpay Settings
echo RAZORPAY_KEY_ID=rzp_test_7HVw0jZ1xbH7Zv
echo RAZORPAY_KEY_SECRET=QyXs5O6YcQtv9mOGGjQ7qvRi
) > .env.new

echo Environment configuration created as .env.new
echo Please rename it to .env if it looks correct

echo.
echo Creating PostgreSQL database...

:: Create the database
echo Creating database '%DB_NAME%'...
psql -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -c "CREATE DATABASE %DB_NAME% WITH ENCODING 'UTF8';" postgres
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to create database. Please check your PostgreSQL installation and credentials.
    pause
    exit /b 1
)

echo.
echo Database created successfully!
echo.
echo Next steps:
echo 1. Rename .env.new to .env if it looks correct
echo 2. Run 'python migrate_to_postgres.py' to migrate your data from SQLite to PostgreSQL
echo 3. Once migration is complete, test your application with 'python manage.py runserver'
echo.

pause 