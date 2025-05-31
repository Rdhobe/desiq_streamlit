from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_merge_20250514_1411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='mbti_type',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='decision_style',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='primary_bias',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ] 