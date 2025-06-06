# Generated by Django 5.1.3 on 2025-05-28 17:39

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_communitymessage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='communitymessage',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='directmessage',
            name='is_read',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='directmessage',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddIndex(
            model_name='communitymessage',
            index=models.Index(fields=['sender', 'timestamp'], name='core_commun_sender__27733e_idx'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['sender', 'recipient'], name='core_direct_sender__cf239d_idx'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['recipient', 'is_read'], name='core_direct_recipie_1cdcee_idx'),
        ),
    ]
