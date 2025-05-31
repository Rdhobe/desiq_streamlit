# SQLite to PostgreSQL Migration Steps

This document provides step-by-step instructions to migrate your DesiQ application from SQLite to PostgreSQL.

## 1. Install PostgreSQL

First, you need to install PostgreSQL on your system:

1. Download PostgreSQL installer from https://www.postgresql.org/download/windows/
2. Run the installer and follow these steps:
   - Select the components to install (at minimum, select the PostgreSQL Server and Command Line Tools)
   - Choose an installation directory (default is fine)
   - Set a password for the 'postgres' user (use 'postgres' for simplicity)
   - Choose the default port 5432
   - Choose the default locale
   - Complete the installation
3. Make sure the PostgreSQL bin directory is added to your system PATH
   - The default location is typically `C:\Program Files\PostgreSQL\15\bin` (version number may vary)
   - To test, open a new command prompt and run `psql --version`

## 2. Create a PostgreSQL Database

You can use our helper script to create the database:

```bash
.\setup_postgres.bat
```

If prompted:
- Database name: `desiq_db`
- User: `postgres`
- Password: `postgres` (or the password you set during installation)
- Host: `localhost`
- Port: `5432`

## 3. Migrate Data from SQLite to PostgreSQL

Run our migration script:

```bash
python migrate_to_postgres.py
```

This script will:
1. Create a backup of your SQLite database
2. Export data to JSON fixtures
3. Create the PostgreSQL schema
4. Import data from fixtures to PostgreSQL
5. Verify the migration

## 4. Verify the Migration

After the migration is complete, you can test your application:

```bash
python manage.py runserver
```

Access the application in your browser and verify everything is working correctly.

## Troubleshooting

### PostgreSQL is not found

If you get an error that PostgreSQL is not installed:
1. Make sure PostgreSQL is installed
2. Add the bin directory to your PATH
3. Restart your command prompt/terminal

### Connection issues

If you encounter connection issues:
1. Verify PostgreSQL service is running:
   ```bash
   # Check the service status
   net start postgresql
   ```
2. Check if the database exists:
   ```bash
   psql -U postgres -c "\l" | findstr desiq_db
   ```
3. Verify port 5432 is not blocked by a firewall

### Password authentication issues

If you have issues with the password:
1. Make sure you're using the correct password for the postgres user
2. Try connecting manually:
   ```bash
   psql -U postgres -h localhost
   ```

## Reverting to SQLite

If you need to revert to SQLite for any reason:
1. Change the database settings back to use SQLite
2. The SQLite database backup is available at `db_backup.sqlite3` 