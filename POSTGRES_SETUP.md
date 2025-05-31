# PostgreSQL Setup for DesiQ

This document provides instructions for switching from SQLite to PostgreSQL in your DesiQ application.

## Why PostgreSQL?

PostgreSQL offers several advantages over SQLite:

1. **Better concurrency**: Handles multiple users/connections efficiently
2. **Scalability**: Can handle larger datasets and more complex queries
3. **Advanced features**: Includes full-text search, JSON support, and more
4. **Production-ready**: Suitable for deployment in production environments
5. **Data integrity**: Provides ACID compliance and transaction support

## Prerequisites

- Python 3.8 or higher
- Django 5.1 or higher
- PostgreSQL 12 or higher

## Installation Steps

### 1. Install PostgreSQL

#### Windows:
1. Download PostgreSQL installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the instructions
3. Set a password for the `postgres` user during installation
4. Make sure to add PostgreSQL bin directory to your PATH

#### macOS:
```bash
brew install postgresql
brew services start postgresql
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create a PostgreSQL Database

You can use the provided helper script on Windows:

```bash
setup_postgres.bat
```

Or manually create a database:

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# In the PostgreSQL console
CREATE DATABASE desiq_db;
CREATE USER desiq_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE desiq_db TO desiq_user;
\q
```

### 3. Configure Environment Variables

Create or update your `.env` file with the following PostgreSQL configuration:

```
# PostgreSQL Database Settings
DATABASE_URL=postgres://username:password@localhost:5432/desiq_db
DB_NAME=desiq_db
DB_USER=username
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Migrate Data from SQLite to PostgreSQL

We've provided a migration script to help transfer your data:

```bash
python migrate_to_postgres.py
```

The script will:
1. Create a backup of your SQLite database
2. Export data to JSON fixtures
3. Configure the application for PostgreSQL
4. Create the PostgreSQL schema
5. Import data from fixtures to PostgreSQL
6. Verify the migration

### 5. Test the Application

After migration, start the application to verify everything works:

```bash
python manage.py runserver
```

## Troubleshooting

### Connection Issues

If you have trouble connecting to PostgreSQL:

1. Check if PostgreSQL service is running:
   ```bash
   # Windows
   net start postgresql

   # macOS
   brew services list

   # Linux
   sudo systemctl status postgresql
   ```

2. Verify your credentials in the `.env` file
3. Make sure the PostgreSQL port (default: 5432) is not blocked by a firewall

### Migration Issues

If the migration script fails:

1. Check PostgreSQL logs for errors
2. Verify that PostgreSQL user has appropriate permissions
3. Try running migrations manually:
   ```bash
   python manage.py migrate
   ```

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Django with PostgreSQL Documentation](https://docs.djangoproject.com/en/5.1/ref/databases/#postgresql-notes)
- [Django Migration Guide](https://docs.djangoproject.com/en/5.1/topics/migrations/) 