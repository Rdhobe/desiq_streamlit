from django.db import migrations, models


def add_issue_type_if_not_exists(apps, schema_editor):
    # Get the db connection
    connection = schema_editor.connection
    cursor = connection.cursor()
    
    # Check if the column already exists
    if connection.vendor == 'postgresql':
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'core_supportissue' AND column_name = 'issue_type';"
        )
        if cursor.fetchone():
            # Column already exists, do nothing
            return
    elif connection.vendor == 'sqlite':
        cursor.execute("PRAGMA table_info(core_supportissue);")
        for col_info in cursor.fetchall():
            if col_info[1] == 'issue_type':  # Column name is at index 1
                # Column already exists, do nothing
                return
    
    # If we're here, the column doesn't exist and should be added
    # The AddField operation below will handle it


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_create_default_superuser'),
    ]

    operations = [
        migrations.RunPython(
            add_issue_type_if_not_exists,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.SeparateDatabaseAndState(
            # Database operation - only executes if our RunPython didn't find the column
            database_operations=[
                migrations.AddField(
                    model_name='supportissue',
                    name='issue_type',
                    field=models.CharField(
                        choices=[
                            ('bug', 'Bug Report'),
                            ('feature', 'Feature Request'),
                            ('question', 'Question'),
                            ('feedback', 'Feedback'),
                            ('contact', 'Contact Form'),
                            ('other', 'Other'),
                        ],
                        default='other',
                        max_length=20,
                    ),
                ),
            ],
            # State operation - always updates Django's internal model state
            state_operations=[
                migrations.AddField(
                    model_name='supportissue',
                    name='issue_type',
                    field=models.CharField(
                        choices=[
                            ('bug', 'Bug Report'),
                            ('feature', 'Feature Request'),
                            ('question', 'Question'),
                            ('feedback', 'Feedback'),
                            ('contact', 'Contact Form'),
                            ('other', 'Other'),
                        ],
                        default='other',
                        max_length=20,
                    ),
                ),
            ],
        ),
    ] 