# Deploying DesiQ to Render with PostgreSQL

This document provides instructions for deploying your DesiQ application to Render using PostgreSQL.

## Prerequisites

- A Render account
- Your DesiQ codebase in a Git repository
- PostgreSQL database (will be created on Render)

## Deployment Steps

### 1. Push Your Code to a Git Repository

Make sure your code is pushed to a Git repository (GitHub, GitLab, or Bitbucket) that Render can access.

### 2. Create a New Web Service on Render

1. Log in to your Render account
2. Click on "New" and select "Blueprint" to use the configuration from render.yaml
3. Connect your Git repository
4. Render will detect the render.yaml file and set up the web service and PostgreSQL database

### 3. Environment Variables

The render.yaml file already specifies the required environment variables, but you may need to set additional ones:

- `OPENAI_API_KEY` - Your OpenAI API key (if used)
- `RAZORPAY_KEY_ID` - Your Razorpay key ID (if used)
- `RAZORPAY_KEY_SECRET` - Your Razorpay key secret (if used)

### 4. Database Migration

The deployment will automatically run migrations, but if you need to seed data:

1. Connect to your Render PostgreSQL database from your local machine using the External Database URL
2. Use the pgAdmin tool or the command line to import data:
   ```bash
   # Export data from local PostgreSQL
   pg_dump -U postgres -h localhost -d desiq_db > desiq_data.sql
   
   # Import to Render PostgreSQL
   psql -U your_render_user -h render_db_host -d desiq your_render_password < desiq_data.sql
   ```

## PostgreSQL Connection URLs

Render provides two connection URLs for your PostgreSQL database:

1. **Internal Database URL**: Used by your web service on Render. This is automatically configured.
2. **External Database URL**: Used for connecting to your database from outside Render (e.g., from your local machine).

## Monitoring and Logs

After deployment:

1. Monitor the build and deployment logs on Render
2. Check that the database migrations run successfully
3. Verify that the application is working by accessing the URL provided by Render

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues:

1. Verify that the DATABASE_URL environment variable is properly set
2. Check that the database service is running on Render
3. Look at the logs for any connection errors

### Migration Failures

If migrations fail:

1. Check the deploy logs for specific error messages
2. Try running migrations manually through the Render shell:
   ```bash
   python manage.py migrate
   ```

### Static Files Issues

If static files aren't being served properly:

1. Ensure STATIC_URL and STATIC_ROOT are set correctly
2. Verify that collectstatic runs during deployment
3. Check that whitenoise middleware is configured correctly

## Scaling and Upgrades

Render offers different pricing tiers for both web services and databases. As your application grows, you can:

1. Upgrade your web service to a higher tier for better performance
2. Upgrade your PostgreSQL database to a paid plan for more storage and connections
3. Set up autoscaling if your application has variable traffic patterns

## Database Backups

Render automatically creates daily backups of your PostgreSQL database on paid plans. You can also create manual backups:

1. Go to your database service in the Render dashboard
2. Click on the "Backups" tab
3. Click "Manual Backup" to create an immediate backup 