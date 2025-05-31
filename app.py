"""
Redirector for Render deployment.
This file helps Render find the correct WSGI application.
"""

import os
import sys
import shutil
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("app")

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')

# Force create session table before anything else
def force_create_session_table():
    """Directly create the session table in the database"""
    logger.info("Starting direct session table creation...")
    
    # First try the Django way
    try:
        # Try importing Django settings
        from django.conf import settings
        if not settings.configured:
            logger.warning("Django settings not configured yet")
            # Try the direct database approach
    except Exception as settings_ex:
        logger.warning(f"Django settings not available: {settings_ex}")
        # Continue with direct approach
    
    # Direct database connection approach
    try:
        # Try to import the required modules
        try:
            import psycopg2
            import dj_database_url
        except ImportError as ie:
            logger.error(f"Required module not found: {ie}")
            return False
            
        # Get connection info from DATABASE_URL
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
            
        logger.info(f"Connecting using DATABASE_URL...")
        
        try:
            # Parse DATABASE_URL
            db_config = dj_database_url.parse(db_url)
            
            if 'postgres' not in db_config.get('ENGINE', ''):
                logger.warning(f"Not a PostgreSQL database: {db_config.get('ENGINE')}")
                return False
                
            # Connect to the database - log everything except password
            connection_info = {
                'dbname': db_config.get('NAME'),
                'user': db_config.get('USER'),
                'host': db_config.get('HOST'),
                'port': db_config.get('PORT', 5432)
            }
            logger.info(f"Connecting to PostgreSQL: {connection_info}")
            
            # Establish connection
            conn = psycopg2.connect(
                dbname=db_config.get('NAME'),
                user=db_config.get('USER'),
                password=db_config.get('PASSWORD'),
                host=db_config.get('HOST'),
                port=db_config.get('PORT', 5432)
            )
            conn.autocommit = True
            
            # Check if table exists
            with conn.cursor() as cursor:
                # Check if session table exists
                cursor.execute("SELECT to_regclass('public.django_session')")
                exists = cursor.fetchone()[0] is not None
                
                if exists:
                    logger.info("Session table already exists in database")
                    conn.close()
                    return True
                
                logger.warning("Session table doesn't exist, creating it...")
                # Create the session table
                cursor.execute("""
                CREATE TABLE django_session (
                    session_key varchar(40) NOT NULL PRIMARY KEY,
                    session_data text NOT NULL,
                    expire_date timestamp with time zone NOT NULL
                );
                """)
                
                # Create index
                cursor.execute("""
                CREATE INDEX django_session_expire_date_idx ON django_session (expire_date);
                """)
                
                # Verify table was created
                cursor.execute("SELECT to_regclass('public.django_session')")
                success = cursor.fetchone()[0] is not None
                
                if success:
                    logger.info("Successfully created django_session table via SQL")
                else:
                    logger.error("Failed to verify django_session table creation")
                    
            conn.close()
            return success
        except Exception as db_ex:
            logger.error(f"Database error in session table creation: {db_ex}", exc_info=True)
            return False
    except Exception as ex:
        logger.error(f"Unexpected error in force_create_session_table: {ex}", exc_info=True)
        return False

# Force create session table before Django is initialized
logger.info("Ensuring session table exists before initialization...")
try:
    success = force_create_session_table()
    logger.info(f"Session table creation result: {'Success' if success else 'Failed'}")
except Exception as ex:
    logger.error(f"Failed to create session table: {ex}", exc_info=True)

# Define a fallback WSGI app for health checks
def fallback_app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path in ('/health', '/health/'):
        status = '200 OK'
        headers = [('Content-type', 'application/json')]
        start_response(status, headers)
        return [b'{"status":"fallback","message":"Application in fallback mode"}']

    status = '500 Internal Server Error'
    headers = [('Content-type', 'text/html; charset=utf-8')]
    start_response(status, headers)
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Maintenance</title></head>
    <body>
        <h1>Maintenance</h1>
        <p>The application is starting or under maintenance. This page refreshes every 10 seconds.</p>
        <meta http-equiv="refresh" content="10">
    </body>
    </html>
    """
    return [html.encode('utf-8')]

def setup_session_table():
    """Explicitly create the session table if it doesn't exist"""
    try:
        # First check if table exists
        from django.db import connection
        
        try:
            # Ensure we're using database sessions
            from django.conf import settings
            if hasattr(settings, 'SESSION_ENGINE') and 'db' not in settings.SESSION_ENGINE:
                logger.warning(f"Session engine not using database: {settings.SESSION_ENGINE}")
            else:
                logger.info(f"Session engine: {getattr(settings, 'SESSION_ENGINE', 'default')}")
        except Exception as settings_ex:
            logger.warning(f"Could not check session engine: {settings_ex}")
        
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("SELECT to_regclass('public.django_session')")
                exists = cursor.fetchone()[0] is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_session';")
                exists = bool(cursor.fetchone())
        
        if exists:
            logger.info("Session table already exists")
            return True
            
        # Try Django migration first
        logger.info("Session table missing, attempting to create via migration")
        try:
            from django.core.management import call_command
            call_command('migrate', 'sessions', verbosity=1, interactive=False)
            return True
        except Exception as e:
            logger.error(f"Migration-based session table creation failed: {e}")
            
        # Direct SQL approach as fallback
        logger.warning("Attempting direct SQL creation of session table")
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                CREATE TABLE django_session (
                    session_key varchar(40) NOT NULL PRIMARY KEY,
                    session_data text NOT NULL,
                    expire_date timestamp with time zone NOT NULL
                );
                CREATE INDEX IF NOT EXISTS django_session_expire_date_idx 
                    ON django_session (expire_date);
                """)
                connection.commit()
                logger.info("Session table created successfully with SQL")
                return True
            else:
                cursor.execute("""
                CREATE TABLE django_session (
                    session_key varchar(40) NOT NULL PRIMARY KEY,
                    session_data text NOT NULL,
                    expire_date datetime NOT NULL
                );
                CREATE INDEX IF NOT EXISTS django_session_expire_date_idx 
                    ON django_session (expire_date);
                """)
                logger.info("Session table created successfully with SQL")
                return True
                
    except Exception as ex:
        logger.critical(f"Failed to create session table: {ex}")
        return False

# Map of application names to their crucial tables
APP_TABLES = {
    'sessions': ['django_session'],
    'auth': ['auth_user', 'auth_group', 'auth_permission'],
    'contenttypes': ['django_content_type'],
}

def run_migrations():
    """Run Django migrations with retry logic"""
    from django.core.management import call_command
    from django.db import connection
    
    max_retries = 3
    retry_interval = 2  # seconds
    problematic_migrations = set()  # Track migrations that had issues
    
    # First ensure critical tables exist
    setup_session_table()
    
    # Run migrations
    for attempt in range(max_retries):
        try:
            logger.info(f"Running migrations (attempt {attempt + 1}/{max_retries})...")
            
            # Try first with regular migrations
            if problematic_migrations:
                # Some migrations failed before, use selective approach
                
                # First migrate standard Django apps
                for app_name in ['admin', 'auth', 'contenttypes', 'sessions']:
                    try:
                        logger.info(f"Migrating {app_name} app...")
                        call_command('migrate', app_name, verbosity=1, interactive=False)
                    except Exception as ex:
                        logger.warning(f"Failed regular migration for {app_name}: {ex}")
                
                # Then social_django app
                try:
                    logger.info("Migrating social_django app...")
                    call_command('migrate', 'social_django', verbosity=1, interactive=False)
                except Exception as ex:
                    logger.warning(f"Failed migration for social_django: {ex}")
                    # If migration fails, try to create tables directly
                    setup_social_auth_tables()
                
                # Finally core migrations that are problematic
                try:
                    logger.info("Applying core migrations with --fake for problematic ones...")
                    call_command('migrate', 'core', verbosity=1, interactive=False)
                except Exception as ex:
                    logger.warning(f"Error during core migration: {ex}")
            else:
                # First attempt, try normal migrations
                call_command('migrate', verbosity=1, interactive=False)
            
            # Do one final check for critical tables
            with connection.cursor() as cursor:
                # Check session table
                if connection.vendor == 'postgresql':
                    cursor.execute("SELECT to_regclass('public.django_session')")
                    session_exists = cursor.fetchone()[0] is not None
                    
                    # Check social auth table
                    cursor.execute("SELECT to_regclass('public.social_auth_usersocialauth')")
                    social_auth_exists = cursor.fetchone()[0] is not None
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_session';")
                    session_exists = bool(cursor.fetchone())
                    
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_auth_usersocialauth';")
                    social_auth_exists = bool(cursor.fetchone())
                    
            if not session_exists:
                logger.warning("Session table still missing after migrations, creating directly")
                setup_session_table()
                
            if not social_auth_exists:
                logger.warning("Social auth tables still missing after migrations, creating directly")
                setup_social_auth_tables()
            
            logger.info("Migrations completed successfully.")
            return True
            
        except Exception as ex:
            error_str = str(ex).lower()
            
            # Check for specific errors
            if "already exists" in error_str and ("column" in error_str or "relation" in error_str):
                logger.warning(f"Detected migration error for existing structure: {ex}")
                
                # Try to extract the app name from the error message
                # Example: "column issue_type of relation core_supportissue already exists"
                parts = error_str.split('_')
                if len(parts) > 1:
                    app_name = parts[0].split()[-1]  # Extract the app name
                    problematic_migrations.add(app_name)
                    logger.info(f"Added {app_name} to problematic migrations list")
                
                # Try a different approach on next iteration
                continue
            
            logger.error(f"Migration error: {ex}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
                retry_interval *= 2  # Exponential backoff
    
    # Last resort - direct create
    setup_session_table()
    setup_social_auth_tables()
    
    logger.critical("All migration attempts failed!")
    return False

def setup_social_auth_tables():
    """Create the social auth tables if they don't exist"""
    try:
        from django.db import connection
        from django.conf import settings
        
        logger.info("Checking for social_auth tables after Django initialization")
        
        # Tables needed for social_auth
        social_tables = [
            {
                'name': 'social_auth_association',
                'sql_postgresql': """
                    CREATE TABLE social_auth_association (
                        id SERIAL PRIMARY KEY,
                        server_url VARCHAR(255) NOT NULL,
                        handle VARCHAR(255) NOT NULL,
                        secret VARCHAR(255) NOT NULL,
                        issued INTEGER NOT NULL,
                        lifetime INTEGER NOT NULL,
                        assoc_type VARCHAR(64) NOT NULL
                    );
                """,
                'sql_sqlite': """
                    CREATE TABLE social_auth_association (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_url VARCHAR(255) NOT NULL,
                        handle VARCHAR(255) NOT NULL,
                        secret VARCHAR(255) NOT NULL,
                        issued INTEGER NOT NULL,
                        lifetime INTEGER NOT NULL,
                        assoc_type VARCHAR(64) NOT NULL
                    );
                """
            },
            {
                'name': 'social_auth_code',
                'sql_postgresql': """
                    CREATE TABLE social_auth_code (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(254) NOT NULL,
                        code VARCHAR(32) NOT NULL,
                        verified BOOLEAN NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                    );
                    CREATE INDEX social_auth_code_code_idx ON social_auth_code (code);
                    CREATE INDEX social_auth_code_timestamp_idx ON social_auth_code (timestamp);
                """,
                'sql_sqlite': """
                    CREATE TABLE social_auth_code (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email VARCHAR(254) NOT NULL,
                        code VARCHAR(32) NOT NULL,
                        verified BOOLEAN NOT NULL,
                        timestamp DATETIME NOT NULL
                    );
                    CREATE INDEX social_auth_code_code_idx ON social_auth_code (code);
                    CREATE INDEX social_auth_code_timestamp_idx ON social_auth_code (timestamp);
                """
            },
            {
                'name': 'social_auth_nonce',
                'sql_postgresql': """
                    CREATE TABLE social_auth_nonce (
                        id SERIAL PRIMARY KEY,
                        server_url VARCHAR(255) NOT NULL,
                        timestamp INTEGER NOT NULL,
                        salt VARCHAR(65) NOT NULL
                    );
                    CREATE UNIQUE INDEX social_auth_nonce_server_url_timestamp_salt_idx 
                    ON social_auth_nonce (server_url, timestamp, salt);
                """,
                'sql_sqlite': """
                    CREATE TABLE social_auth_nonce (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_url VARCHAR(255) NOT NULL,
                        timestamp INTEGER NOT NULL,
                        salt VARCHAR(65) NOT NULL
                    );
                    CREATE UNIQUE INDEX social_auth_nonce_server_url_timestamp_salt_idx 
                    ON social_auth_nonce (server_url, timestamp, salt);
                """
            },
            {
                'name': 'social_auth_partial',
                'sql_postgresql': """
                    CREATE TABLE social_auth_partial (
                        id SERIAL PRIMARY KEY,
                        token VARCHAR(32) NOT NULL,
                        next_step INTEGER NOT NULL,
                        backend VARCHAR(32) NOT NULL,
                        data TEXT NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                    );
                    CREATE INDEX social_auth_partial_token_idx ON social_auth_partial (token);
                    CREATE INDEX social_auth_partial_timestamp_idx ON social_auth_partial (timestamp);
                """,
                'sql_sqlite': """
                    CREATE TABLE social_auth_partial (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        token VARCHAR(32) NOT NULL,
                        next_step INTEGER NOT NULL,
                        backend VARCHAR(32) NOT NULL,
                        data TEXT NOT NULL,
                        timestamp DATETIME NOT NULL
                    );
                    CREATE INDEX social_auth_partial_token_idx ON social_auth_partial (token);
                    CREATE INDEX social_auth_partial_timestamp_idx ON social_auth_partial (timestamp);
                """
            },
            {
                'name': 'social_auth_usersocialauth',
                'sql_postgresql': """
                    CREATE TABLE social_auth_usersocialauth (
                        id SERIAL PRIMARY KEY,
                        provider VARCHAR(32) NOT NULL,
                        uid VARCHAR(255) NOT NULL,
                        extra_data TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        created TIMESTAMP WITH TIME ZONE NOT NULL,
                        modified TIMESTAMP WITH TIME ZONE NOT NULL,
                        CONSTRAINT social_auth_usersocialauth_user_id_fkey FOREIGN KEY (user_id) 
                            REFERENCES auth_user (id) ON DELETE CASCADE
                    );
                    CREATE UNIQUE INDEX social_auth_usersocialauth_provider_uid_idx 
                    ON social_auth_usersocialauth (provider, uid);
                """,
                'sql_sqlite': """
                    CREATE TABLE social_auth_usersocialauth (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        provider VARCHAR(32) NOT NULL,
                        uid VARCHAR(255) NOT NULL,
                        extra_data TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        created DATETIME NOT NULL,
                        modified DATETIME NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE
                    );
                    CREATE UNIQUE INDEX social_auth_usersocialauth_provider_uid_idx 
                    ON social_auth_usersocialauth (provider, uid);
                """
            }
        ]
        
        with connection.cursor() as cursor:
            # Check for each social auth table and create if missing
            for table_info in social_tables:
                table_name = table_info['name']
                
                # Check if table exists
                if connection.vendor == 'postgresql':
                    cursor.execute("SELECT to_regclass('public.%s')" % table_name)
                    exists = cursor.fetchone()[0] is not None
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s';" % table_name)
                    exists = bool(cursor.fetchone())
                
                if exists:
                    logger.info(f"Table {table_name} already exists")
                    continue
                
                # Create the table
                logger.warning(f"Table {table_name} is missing, creating it...")
                
                # Get the SQL for this database type
                if connection.vendor == 'postgresql':
                    sql = table_info['sql_postgresql']
                else:
                    sql = table_info['sql_sqlite']
                
                try:
                    cursor.execute(sql)
                    if connection.vendor == 'postgresql':
                        connection.commit()
                    
                    logger.info(f"Successfully created table {table_name}")
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")
                    
        # Run a final migration to ensure everything is caught
        try:
            from django.core.management import call_command
            logger.info("Running migrate for social_django app...")
            call_command('migrate', 'social_django', verbosity=1, interactive=False)
        except Exception as e:
            logger.error(f"Error running social_django migrations: {e}")
            
        return True
    except Exception as ex:
        logger.error(f"Error in setup_social_auth_tables: {ex}", exc_info=True)
        return False

try:
    # Get the Django application with WhiteNoise
    from django.core.wsgi import get_wsgi_application
    from whitenoise import WhiteNoise
    import django

    # Set up Django
    django.setup()
    from django.conf import settings
    
    # Force setup session table as very first step after Django setup
    session_table_exists = setup_session_table()
    logger.info(f"Session table exists check: {session_table_exists}")
    
    # Set up social auth tables
    social_tables_setup = setup_social_auth_tables()
    logger.info(f"Social auth tables setup: {social_tables_setup}")
    
    # Check for essential tables using a reliable method
    logger.info("Verifying database schema...")
    try:
        from django.db import connection, OperationalError

        # First, ensure database is ready
        retries = 5
        while retries > 0:
            try:
                connection.ensure_connection()
                if connection.is_usable():
                    logger.info(f"Database connected successfully: {connection.vendor}")
                    break
                else:
                    logger.warning("Database connection not usable, retrying...")
            except OperationalError as e:
                retries -= 1
                if retries == 0:
                    logger.error(f"Failed to connect to database after 5 attempts: {e}")
                    raise
                logger.warning(f"Database connection error ({e}), retrying in 2s... ({retries} attempts left)")
                time.sleep(2)
        
        # Now check for critical tables
        critical_tables = ['auth_user', 'django_content_type', 'django_session', 'django_migrations']
        missing_tables = []
        
        with connection.cursor() as cursor:
            for table in critical_tables:
                if connection.vendor == 'postgresql':
                    cursor.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)", [table])
                    exists = cursor.fetchone()[0]
                else:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
                    exists = bool(cursor.fetchone())
                
                if not exists:
                    missing_tables.append(table)
                    
        if missing_tables:
            logger.warning(f"Missing tables detected: {', '.join(missing_tables)}")
            
            # First, try to run specific migrations for missing tables
            if 'django_session' in missing_tables:
                setup_session_table()
            
            # Then run migrations for everything else
            run_migrations()
            
            # Verify tables were created
            with connection.cursor() as cursor:
                for table in missing_tables:
                    if connection.vendor == 'postgresql':
                        cursor.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)", [table])
                        exists = cursor.fetchone()[0]
                    else:
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
                        exists = bool(cursor.fetchone())
                    logger.info(f"Table {table} created: {exists}")
    except Exception as ex:
        logger.error(f"Database check error: {ex}")
        # Attempt migrations anyway as a last resort
        run_migrations()

    # Log static settings
    logger.info("Django initialized, settings loaded")
    logger.info(f"STATIC_URL: {settings.STATIC_URL}")
    logger.info(f"STATIC_ROOT: {settings.STATIC_ROOT}")

    # Handle static files manually if needed
    if os.path.exists(settings.STATIC_ROOT) and not os.listdir(settings.STATIC_ROOT):
        for static_dir in settings.STATICFILES_DIRS:
            if os.path.exists(static_dir):
                for root, dirs, files in os.walk(static_dir):
                    for file in files:
                        src = os.path.join(root, file)
                        rel_path = os.path.relpath(src, static_dir)
                        dst = os.path.join(settings.STATIC_ROOT, rel_path)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        logger.info(f"Copied {src} → {dst}")

    # WSGI application with WhiteNoise
    django_app = get_wsgi_application()
    app = WhiteNoise(django_app)
    app.add_files(settings.STATIC_ROOT, prefix=settings.STATIC_URL.strip('/') + '/')
    application = app

    logger.info("WhiteNoise configured successfully.")

except Exception as e:
    import traceback
    logger.critical(f"Startup error: {e}")
    logger.critical(traceback.format_exc())
    logger.warning("Fallback mode activated.")
    app = application = fallback_app
