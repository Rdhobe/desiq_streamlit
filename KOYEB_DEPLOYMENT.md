# Deploying DesiQ to Koyeb

This document provides instructions for deploying your DesiQ application to Koyeb.

## Prerequisites

- A Koyeb account
- Your DesiQ codebase pushed to a Git repository
- PostgreSQL database (you can use Koyeb's database service or an external database)

## Deployment Steps

### 1. Push Your Code to a Git Repository

Ensure your code is pushed to a Git repository (GitHub, GitLab, or Bitbucket) that Koyeb can access.

### 2. Set Up Database

You have two options:

1. **Use Koyeb's Database Service**:
   - In Koyeb dashboard, go to the Database section
   - Create a new PostgreSQL database
   - Note the connection string for later

2. **Use External Database** (e.g., Render, Supabase, or other PostgreSQL provider):
   - Note the connection string for your database

### 3. Create Secrets in Koyeb

Before deploying, create the following secrets in Koyeb:

1. Go to the Koyeb dashboard
2. Navigate to the Secrets section
3. Create the following secrets:
   - `secret-key`: A strong random Django secret key
   - `database-url`: Your PostgreSQL connection string
   - `openai-api-key`: Your OpenAI API key (if used)
   - `razorpay-key-id`: Your Razorpay key ID (if used)
   - `razorpay-key-secret`: Your Razorpay key secret (if used)

### 4. Deploy the Application

#### Option 1: Using Koyeb Dashboard (Manual)

1. Log in to your Koyeb account
2. Click on "Create App"
3. Choose "GitHub" as your deployment method
4. Select your repository and branch
5. Configure the deployment settings:
   - Name: `desiq`
   - Region: Choose the region closest to your users
   - Instance type: Start with Nano
   - Environment variables: Add all the environment variables from `koyeb.yaml`
   - Build method: Docker
   - Port: 8000
6. Click "Deploy"

#### Option 2: Using Koyeb CLI (Recommended)

1. Install the Koyeb CLI:
   ```bash
   # For macOS
   brew install koyeb/tap/cli
   
   # For Linux
   curl -fsSL https://cli.koyeb.com/install.sh | bash
   ```

2. Login to your Koyeb account:
   ```bash
   koyeb login
   ```

3. Deploy using the koyeb.yaml file:
   ```bash
   koyeb app init --name desiq --git github.com/yourusername/desiq --git-branch main
   ```

4. Verify deployment:
   ```bash
   koyeb service get desiq
   ```

### 5. Database Migration

The deployment will automatically run migrations during the Docker build process. If you need to run migrations manually:

1. Use the Koyeb dashboard or CLI to open a shell in your application:
   ```bash
   koyeb shell exec --app desiq
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

## Docker Deployment Details

The project includes a Dockerfile that:

1. Uses Python 3.11 slim as the base image
2. Installs all dependencies from requirements.txt
3. Copies the project files
4. Collects static files
5. Runs the Django application using Gunicorn

The Docker build process handles:
- Installing the correct version of Django
- Setting up static files
- Preparing the application for production

## Monitoring and Logs

After deployment:

1. Monitor the build and deployment logs in the Koyeb dashboard
2. Check that the database migrations run successfully
3. Verify that the application is working by accessing the URL provided by Koyeb

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues:

1. Verify that the DATABASE_URL secret is correctly set
2. Check if your database service is running and accessible
3. Look at the logs for any connection errors

### Static Files Issues

If static files aren't being served properly:

1. Ensure STATIC_URL and STATIC_ROOT are set correctly
2. Verify that collectstatic runs during deployment
3. Check that whitenoise middleware is configured correctly

## Scaling

Koyeb makes it easy to scale your application:

1. Horizontal scaling: Adjust the min/max instances in the scaling section
2. Vertical scaling: Change the instance type (Nano, Micro, Small, etc.)

## Persistent Storage

For applications requiring persistent storage (for user uploads, etc.):

1. Use Koyeb's volume service to create a persistent volume
2. Attach the volume to your application and configure the mount path

## Custom Domain

To use a custom domain with your Koyeb app:

1. Go to the Domains section in the Koyeb dashboard
2. Add your domain and verify ownership
3. Update your DNS settings to point to the Koyeb app

## SSL/TLS

Koyeb automatically provisions and manages SSL/TLS certificates for your custom domains. 