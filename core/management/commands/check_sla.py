"""
Django management command to check SLA and auto-escalate breaches
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from core.models import Request, RequestHistory
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check SLA deadlines and auto-escalate breached requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be escalated without making changes',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Check requests that have been breached for more than N hours',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        breach_hours = options['hours']
        
        self.stdout.write(self.style.WARNING("\n=== SLA Check (DRY RUN) ===\n"))
        
        # Find all requests with breached SLA that are not closed
        breached_requests = Request.objects.filter(
            Q(status='Assigned') | Q(status='In Progress'),
            sla_deadline__lt=timezone.now()
        )
        
        # Filter by breach duration
        breached_count = 0
        escalated_count = 0
        
        for req in breached_requests:
            breach_duration = timezone.now() - req.sla_deadline
            breach_hours_actual = breach_duration.total_seconds() / 3600
            
            if breach_hours_actual >= breach_hours:
                breached_count += 1
                
                if not req.is_escalated:
                    escalated_count += 1
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"  [WOULD ESCALATE] #{req.id}: {req.patient_name} "
                            f"- SLA breached {breach_hours_actual:.1f}h ago")
                        )
                    else:
                        req.is_escalated = True
                        req.escalation_reason = f"Auto-escalated: SLA breached {breach_hours_actual:.1f} hours ago"
                        req.save()
                        
                        # Log to history
                        RequestHistory.objects.create(
                            request=req,
                            department=req.assigned_department,
                            status=f"Auto-escalated: SLA breached {breach_hours_actual:.1f}h ago"
                        )
                        
                        logger.warning(f"Request {req.id} auto-escalated: SLA breached {breach_hours_actual:.1f}h ago")
                        
                        self.stdout.write(
                            self.style.ERROR(f"  [ESCALATED] #{req.id}: {req.patient_name} "
                            f"- SLA breached {breach_hours_actual:.1f}h ago")
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"  [ALREADY ESCALATED] #{req.id}: {req.patient_name}")
                    )
        
        # Summary
        self.stdout.write(self.style.WARNING("\n=== Summary ==="))
        self.stdout.write(f"Total breached requests: {breached_count}")
        self.stdout.write(f"Newly escalated: {escalated_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n(Dry run - no changes made)"))
        
        self.stdout.write("")
        
        return f"{breached_count} breached, {escalated_count} escalated"
