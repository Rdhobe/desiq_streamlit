# Running DesiQ on Streamlit with Render-like Configuration

This guide explains how to run your DesiQ Django application on Streamlit with a configuration similar to your Render deployment.

## What This Does

The `run_streamlit_render.py` script integrates your existing Django application with Streamlit by:

1. Setting up environment variables similar to your Render deployment
2. Installing required dependencies from render-requirements.txt
3. Preparing static files using the same approach as render-build.sh
4. Running Django migrations
5. Starting the Streamlit server connected to your Django app

## Prerequisites

- Python 3.7+ 
- Django project (as deployed on Render)
- Database configuration (similar to what you have on Render)

## Running the Application

### Step 1: Run the integrated script

```bash
python run_streamlit_render.py
```

This script:
- Sets up environment variables matching your Render configuration
- Installs required dependencies
- Prepares static files
- Runs Django migrations
- Starts the Streamlit server

### Step 2: Access the application

Open your browser and go to:
```
http://localhost:8501
```

## Deployment Options

If you want to deploy this Streamlit version on Render:

1. Add a new Web Service on Render
2. Point to the same repository
3. Set the build command to:
   ```
   pip install -r streamlit_requirements.txt && pip install -r render-requirements.txt
   ```
4. Set the start command to:
   ```
   streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
   ```

## Troubleshooting

### Database Issues

If you see database connection errors:

1. Check your database configuration in Django settings
2. For local development, you might need to modify the `DATABASE_URL` environment variable
3. To use a local database, add this to your settings:
   ```python
   # Local SQLite fallback
   DATABASES['default'] = {
       'ENGINE': 'django.db.backends.sqlite3',
       'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
   } if 'DATABASE_URL' not in os.environ else DATABASES['default']
   ```

### Static Files Issues

If static files are not loading properly:

1. Run the fix_admin_static.py script manually:
   ```
   python fix_admin_static.py
   ```

2. Check that the STATIC_ROOT and STATIC_URL are set correctly:
   ```
   STATIC_ROOT=staticfiles
   STATIC_URL=/static/
   ```

### Streamlit Integration Issues

If Streamlit has trouble connecting to Django:

1. Make sure the Django app is properly initialized in streamlit_app.py
2. Check that environment variables are properly set
3. Ensure that your database is accessible

## Technical Details

The integration works by:

1. Configuring the Django environment before Streamlit starts
2. Loading Django models in the Streamlit app
3. Utilizing the Django ORM for database queries
4. Maintaining the same settings as your Render deployment

This approach allows you to visualize your Django application data through Streamlit while maintaining compatibility with your existing deployment. 