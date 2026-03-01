"""
Management command to seed workflow definitions and category modifiers
"""
from django.core.management.base import BaseCommand
from core.models import WorkflowDefinition, CategoryWorkflowModifier


class Command(BaseCommand):
    help = 'Seed workflow definitions and category modifiers from default configuration'

    def handle(self, *args, **options):
        # Seed Workflow Definitions
        workflow_data = [
            {
                'request_type': 'MRI',
                'workflow_steps': ['Reception', 'Radiology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'X-Ray',
                'workflow_steps': ['Reception', 'Radiology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'CT Scan',
                'workflow_steps': ['Reception', 'Radiology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Ultrasound',
                'workflow_steps': ['Reception', 'Radiology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Cardiac',
                'workflow_steps': ['Reception', 'Cardiology', 'ICU', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'ECG',
                'workflow_steps': ['Reception', 'Cardiology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Blood Test',
                'workflow_steps': ['Reception', 'Pathology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Surgery',
                'workflow_steps': ['Reception', 'Surgery', 'ICU', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'General Checkup',
                'workflow_steps': ['Reception', 'General Medicine', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Dental',
                'workflow_steps': ['Reception', 'Dental', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Eye',
                'workflow_steps': ['Reception', 'Ophthalmology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Optical',
                'workflow_steps': ['Reception', 'Ophthalmology', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Physiotherapy',
                'workflow_steps': ['Reception', 'Physiotherapy', 'Billing'],
                'initial_department': 'Reception',
            },
            {
                'request_type': 'Vaccination',
                'workflow_steps': ['Reception', 'Pharmacy', 'Billing'],
                'initial_department': 'Reception',
            },
        ]

        # Create or update workflow definitions
        created_count = 0
        for wf_data in workflow_data:
            wf, created = WorkflowDefinition.objects.update_or_create(
                request_type=wf_data['request_type'],
                defaults=wf_data
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} workflow definitions'))

        # Seed Category Workflow Modifiers
        category_modifiers = [
            {
                'category': 'Emergency',
                'modifier_type': 'add_front',
                'departments_to_add': ['Emergency'],
                'departments_to_skip': [],
                'apply_to_request_types': [],
                'priority': 100,
            },
            {
                'category': 'Inpatient',
                'modifier_type': 'add_front',
                'departments_to_add': ['Admission'],
                'departments_to_skip': [],
                'apply_to_request_types': [],
                'priority': 50,
            },
            {
                'category': 'Follow-up',
                'modifier_type': 'skip',
                'departments_to_add': [],
                'departments_to_skip': ['Reception'],
                'apply_to_request_types': [],
                'priority': 25,
            },
            {
                'category': 'Outpatient',
                'modifier_type': 'add_front',
                'departments_to_add': [],
                'departments_to_skip': [],
                'apply_to_request_types': [],
                'priority': 0,
            },
        ]

        # Create or update category modifiers
        mod_created = 0
        for mod_data in category_modifiers:
            mod, created = CategoryWorkflowModifier.objects.update_or_create(
                category=mod_data['category'],
                defaults=mod_data
            )
            if created:
                mod_created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {mod_created} category modifiers'))
        self.stdout.write(self.style.SUCCESS('Workflow seeding completed!'))
