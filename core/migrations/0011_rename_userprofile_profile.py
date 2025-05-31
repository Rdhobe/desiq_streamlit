from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_userprofile_decision_style_userprofile_mbti_type_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UserProfile',
            new_name='Profile',
        ),
    ] 