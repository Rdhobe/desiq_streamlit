from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Recreates missing tables in the database'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Create Notification table
            self.stdout.write("Creating missing tables...")
            
            # Create Notification table
            cursor.execute("""
                CREATE TABLE "core_notification" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "title" varchar(255) NOT NULL,
                    "message" text NOT NULL,
                    "notification_type" varchar(50) NOT NULL,
                    "is_read" boolean NOT NULL,
                    "is_email_sent" boolean NOT NULL,
                    "created_at" timestamp with time zone NOT NULL,
                    "user_id" integer NOT NULL,
                    CONSTRAINT "core_notification_user_id_fkey" 
                    FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") 
                    DEFERRABLE INITIALLY DEFERRED
                );
            """)
            
            # Create index on user_id
            cursor.execute("""
                CREATE INDEX "core_notification_user_id_idx" 
                ON "core_notification" ("user_id");
            """)
            
            # Create Conversation table
            cursor.execute("""
                CREATE TABLE "core_conversation" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "last_message" text NULL,
                    "last_message_time" timestamp with time zone NOT NULL,
                    "unread_count" integer NOT NULL,
                    "initiator_id" integer NOT NULL,
                    "receiver_id" integer NOT NULL,
                    CONSTRAINT "core_conversation_initiator_id_fkey" 
                    FOREIGN KEY ("initiator_id") REFERENCES "auth_user" ("id") 
                    DEFERRABLE INITIALLY DEFERRED,
                    CONSTRAINT "core_conversation_receiver_id_fkey" 
                    FOREIGN KEY ("receiver_id") REFERENCES "auth_user" ("id") 
                    DEFERRABLE INITIALLY DEFERRED,
                    CONSTRAINT "core_conversation_initiator_id_receiver_id_uniq" 
                    UNIQUE ("initiator_id", "receiver_id")
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX "core_conversation_initiator_id_idx" 
                ON "core_conversation" ("initiator_id");
            """)
            
            cursor.execute("""
                CREATE INDEX "core_conversation_receiver_id_idx" 
                ON "core_conversation" ("receiver_id");
            """)
            
        self.stdout.write(self.style.SUCCESS("Successfully recreated missing tables")) 