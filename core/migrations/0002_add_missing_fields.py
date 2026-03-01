# Generated manually to add missing fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Add missing fields to Department
        migrations.AddField(
            model_name='department',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='department',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='department',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='department',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        # Add missing fields to Request
        migrations.AddField(
            model_name='request',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        # Add missing fields to RequestHistory
        migrations.AddField(
            model_name='requesthistory',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
