from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Resets social_django migrations and applies them from scratch'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Delete existing migration records for social_django
            cursor.execute("""
                DELETE FROM django_migrations 
                WHERE app = 'social_django';
            """)
            self.stdout.write(self.style.SUCCESS("Reset social_django migrations."))
            
            # Check if any social_auth tables already exist and drop them
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '%social_auth%';
            """)
            existing_tables = cursor.fetchall()
            
            if existing_tables:
                self.stdout.write("Dropping existing social_auth tables:")
                for table in existing_tables:
                    table_name = table[0]
                    self.stdout.write(f"  - Dropping {table_name}")
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
        
        # Create tables manually according to the initial migration
        with connection.cursor() as cursor:
            self.stdout.write("Creating social_auth tables manually...")
            
            # Create Association table
            cursor.execute("""
                CREATE TABLE "social_auth_association" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "server_url" varchar(255) NOT NULL,
                    "handle" varchar(255) NOT NULL,
                    "secret" varchar(255) NOT NULL,
                    "issued" integer NOT NULL,
                    "lifetime" integer NOT NULL,
                    "assoc_type" varchar(64) NOT NULL
                );
            """)
            
            # Create Code table
            cursor.execute("""
                CREATE TABLE "social_auth_code" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "email" varchar(254) NOT NULL,
                    "code" varchar(32) NOT NULL,
                    "verified" boolean NOT NULL,
                    "timestamp" timestamp with time zone NOT NULL
                );
            """)
            
            # Create Nonce table
            cursor.execute("""
                CREATE TABLE "social_auth_nonce" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "server_url" varchar(255) NOT NULL,
                    "timestamp" integer NOT NULL,
                    "salt" varchar(65) NOT NULL
                );
            """)
            
            # Create UserSocialAuth table
            cursor.execute("""
                CREATE TABLE "social_auth_usersocialauth" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "provider" varchar(32) NOT NULL,
                    "uid" varchar(255) NOT NULL,
                    "extra_data" text NOT NULL,
                    "user_id" integer NOT NULL,
                    "created" timestamp with time zone NOT NULL,
                    "modified" timestamp with time zone NOT NULL,
                    CONSTRAINT "social_auth_usersocialauth_user_id_17d28448_fk_auth_user_id" 
                    FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
                );
            """)
            
            # Create index on provider and uid
            cursor.execute("""
                CREATE UNIQUE INDEX "social_auth_usersocialauth_provider_uid_e6b5e668_uniq" 
                ON "social_auth_usersocialauth" ("provider", "uid");
            """)
            
            # Create index on user_id
            cursor.execute("""
                CREATE INDEX "social_auth_usersocialauth_user_id_17d28448" 
                ON "social_auth_usersocialauth" ("user_id");
            """)
            
            # Add timestamp columns to Partial table
            cursor.execute("""
                CREATE TABLE "social_auth_partial" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "token" varchar(32) NOT NULL,
                    "next_step" smallint NOT NULL,
                    "backend" varchar(32) NOT NULL,
                    "data" text NOT NULL,
                    "timestamp" timestamp with time zone NOT NULL
                );
            """)
        
        # Mark migrations as applied
        with connection.cursor() as cursor:
            migrations = [
                '0001_initial',
                '0002_add_related_name',
                '0003_alter_email_max_length',
                '0004_auto_20160423_0400',
                '0005_auto_20160727_2333',
                '0006_partial',
                '0007_code_timestamp',
                '0008_partial_timestamp',
                '0009_auto_20191118_0520',
                '0010_uid_db_index',
                '0011_alter_id_fields',
                '0012_usersocialauth_extra_data_new',
                '0013_migrate_extra_data',
                '0014_remove_usersocialauth_extra_data',
                '0015_rename_extra_data_new_usersocialauth_extra_data',
                '0016_alter_usersocialauth_extra_data',
            ]
            
            for migration in migrations:
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES (%s, %s, NOW());
                """, ['social_django', migration])
        
        # Verify tables were created
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '%social_auth%';
            """)
            created_tables = cursor.fetchall()
            
            if created_tables:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created_tables)} social_auth tables:"))
                for table in created_tables:
                    self.stdout.write(f"  - {table[0]}")
            else:
                self.stdout.write(self.style.ERROR("Failed to create social_auth tables!")) 