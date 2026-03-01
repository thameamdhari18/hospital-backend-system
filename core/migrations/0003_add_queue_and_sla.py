# Migration to add queue tracking and SLA fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_missing_fields'),
    ]

    operations = [
        # Add SLA hours to Department
        migrations.AddField(
            model_name='department',
            name='sla_hours',
            field=models.PositiveIntegerField(default=24, help_text='SLA target time in hours'),
        ),
        
        # Add category to Request
        migrations.AddField(
            model_name='request',
            name='category',
            field=models.CharField(
                choices=[('Outpatient', 'Outpatient'), ('Inpatient', 'Inpatient'), ('Emergency', 'Emergency'), ('Follow-up', 'Follow-up')],
                default='Outpatient',
                help_text='Request category',
                max_length=20
            ),
        ),
        
        # Add queue tracking fields to Request
        migrations.AddField(
            model_name='request',
            name='queue_position',
            field=models.PositiveIntegerField(default=0, help_text='Position in department queue'),
        ),
        migrations.AddField(
            model_name='request',
            name='estimated_wait_time',
            field=models.PositiveIntegerField(default=0, help_text='Estimated wait time in minutes'),
        ),
        
        # Add time tracking fields to Request
        migrations.AddField(
            model_name='request',
            name='assigned_at',
            field=models.DateTimeField(blank=True, help_text='When request was assigned to department', null=True),
        ),
        migrations.AddField(
            model_name='request',
            name='in_progress_at',
            field=models.DateTimeField(blank=True, help_text='When request status changed to In Progress', null=True),
        ),
        migrations.AddField(
            model_name='request',
            name='completed_at',
            field=models.DateTimeField(blank=True, help_text='When request was completed', null=True),
        ),
        
        # Add SLA tracking fields to Request
        migrations.AddField(
            model_name='request',
            name='sla_deadline',
            field=models.DateTimeField(blank=True, help_text='Service Level Agreement deadline', null=True),
        ),
        migrations.AddField(
            model_name='request',
            name='is_escalated',
            field=models.BooleanField(default=False, help_text='Whether request has been escalated'),
        ),
        migrations.AddField(
            model_name='request',
            name='escalation_reason',
            field=models.TextField(blank=True, help_text='Reason for escalation'),
        ),
    ]
