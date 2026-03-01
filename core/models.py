"""
Hospital Workflow System - Models
Database models with validation, indexes, and admin configuration
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Department(models.Model):
    """
    Department model representing hospital departments
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Department name"
    )
    current_load = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0, message="Load cannot be negative"),
        ],
        help_text="Current number of active requests"
    )
    threshold = models.IntegerField(
        default=5,
        validators=[
            MinValueValidator(1, message="Threshold must be at least 1"),
            MaxValueValidator(100, message="Threshold cannot exceed 100"),
        ],
        help_text="Maximum capacity before overload"
    )
    # SLA settings per department
    sla_hours = models.PositiveIntegerField(
        default=24,
        help_text="SLA target time in hours"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Department description"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether department is active"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_overloaded(self):
        """Check if department is overloaded"""
        return self.current_load > self.threshold

    @property
    def available_capacity(self):
        """Calculate available capacity"""
        return max(0, self.threshold - self.current_load)

    @property
    def utilization_percentage(self):
        """Calculate utilization percentage"""
        if self.threshold > 0:
            return round((self.current_load / self.threshold) * 100, 1)
        return 0

    def clean(self):
        """Model-level validation"""
        if self.threshold < 1:
            raise ValidationError({'threshold': 'Threshold must be at least 1'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Request(models.Model):
    """
    Patient request model representing medical service requests
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Closed', 'Closed'),
    ]
    
    # Priority choices
    PRIORITY_CHOICES = [
        ('Normal', 'Normal'),
        ('Emergency', 'Emergency'),
    ]
    
    # Request Category choices
    CATEGORY_CHOICES = [
        ('Outpatient', 'Outpatient'),
        ('Inpatient', 'Inpatient'),
        ('Emergency', 'Emergency'),
        ('Follow-up', 'Follow-up'),
    ]

    patient_name = models.CharField(
        max_length=100,
        help_text="Patient full name"
    )
    request_type = models.CharField(
        max_length=100,
        help_text="Type of medical service requested"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='Normal',
        help_text="Request priority level"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='Outpatient',
        help_text="Request category"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Assigned',
        help_text="Current request status"
    )
    assigned_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        help_text="Department handling this request"
    )
    
    # Queue tracking fields
    queue_position = models.PositiveIntegerField(
        default=0,
        help_text="Position in department queue"
    )
    estimated_wait_time = models.PositiveIntegerField(
        default=0,
        help_text="Estimated wait time in minutes"
    )
    
    # Time tracking fields
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When request was assigned to department"
    )
    in_progress_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When request status changed to In Progress"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When request was completed"
    )
    
    # SLA tracking
    sla_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Service Level Agreement deadline"
    )
    is_escalated = models.BooleanField(
        default=False,
        help_text="Whether request has been escalated"
    )
    escalation_reason = models.TextField(
        blank=True,
        help_text="Reason for escalation"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'queue_position', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['request_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['patient_name']),
            models.Index(fields=['category']),
            models.Index(fields=['queue_position']),
            models.Index(fields=['is_escalated']),
        ]

    def __str__(self):
        return f"{self.patient_name} - {self.request_type}"

    def clean(self):
        """Model-level validation"""
        if self.patient_name and len(self.patient_name.strip()) < 2:
            raise ValidationError({'patient_name': 'Patient name must be at least 2 characters'})
        
        if self.priority not in ['Normal', 'Emergency']:
            raise ValidationError({'priority': 'Invalid priority level'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
    @property
    def is_emergency(self):
        """Check if request is an emergency"""
        return self.priority == 'Emergency'
    
    @property
    def wait_time_minutes(self):
        """Calculate wait time in minutes since creation"""
        if self.assigned_at:
            delta = timezone.now() - self.assigned_at
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def is_sla_breached(self):
        """Check if SLA deadline has passed"""
        if self.sla_deadline and timezone.now() > self.sla_deadline:
            return True
        return False
    
    @property
    def time_until_sla_breach(self):
        """Get minutes until SLA breach (negative if breached)"""
        if self.sla_deadline:
            delta = self.sla_deadline - timezone.now()
            return int(delta.total_seconds() / 60)
        return None
    
    def calculate_queue_position(self):
        """Calculate queue position based on priority and waiting time"""
        if not self.assigned_department:
            return 0
        
        # Get all pending requests in the same department
        pending_requests = Request.objects.filter(
            assigned_department=self.assigned_department,
            status__in=['Assigned', 'In Progress']
        ).exclude(id=self.id)
        
        # Emergency requests get priority
        if self.priority == 'Emergency':
            # Count emergency requests ahead
            emergency_ahead = pending_requests.filter(priority='Emergency').count()
            return emergency_ahead
        
        # Normal requests: count by waiting time
        position = 1
        for req in pending_requests.order_by('-priority', 'created_at'):
            if req.id == self.id:
                break
            position += 1
        return position


class RequestHistory(models.Model):
    """
    Request history model for tracking request state changes
    """
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="The request this history belongs to"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_history',
        help_text="Department at time of this history entry"
    )
    status = models.CharField(
        max_length=100,
        help_text="Status at this point in history"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes for this history entry"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Request histories'
        indexes = [
            models.Index(fields=['request', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.request.patient_name} - {self.status} at {self.timestamp}"


class WorkflowDefinition(models.Model):
    """
    Workflow definition model - stores workflow paths for each request type
    """
    REQUEST_TYPE_CHOICES = [
        ('MRI', 'MRI'),
        ('X-Ray', 'X-Ray'),
        ('CT Scan', 'CT Scan'),
        ('Ultrasound', 'Ultrasound'),
        ('Cardiac', 'Cardiac'),
        ('ECG', 'ECG'),
        ('Blood Test', 'Blood Test'),
        ('Surgery', 'Surgery'),
        ('General Checkup', 'General Checkup'),
        ('Dental', 'Dental'),
        ('Eye', 'Eye'),
        ('Optical', 'Optical'),
        ('Physiotherapy', 'Physiotherapy'),
        ('Vaccination', 'Vaccination'),
    ]
    
    request_type = models.CharField(
        max_length=50,
        choices=REQUEST_TYPE_CHOICES,
        unique=True,
        help_text="Request type this workflow applies to"
    )
    workflow_steps = models.JSONField(
        default=list,
        help_text="List of departments in order (e.g., ['Reception', 'Radiology', 'Billing'])"
    )
    initial_department = models.CharField(
        max_length=100,
        help_text="Initial department for this request type"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this workflow is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['request_type']
        verbose_name = 'Workflow Definition'
        verbose_name_plural = 'Workflow Definitions'

    def __str__(self):
        return f"{self.request_type}: {' -> '.join(self.workflow_steps)}"
    
    def clean(self):
        """Validate workflow steps"""
        if not self.workflow_steps:
            raise ValidationError({'workflow_steps': 'Workflow must have at least one step'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CategoryWorkflowModifier(models.Model):
    """
    Category-based workflow modifiers - modifies base workflow based on category
    """
    CATEGORY_CHOICES = [
        ('Outpatient', 'Outpatient'),
        ('Inpatient', 'Inpatient'),
        ('Emergency', 'Emergency'),
        ('Follow-up', 'Follow-up'),
    ]
    
    MODIFIER_TYPE_CHOICES = [
        ('add_front', 'Add to Front'),
        ('add_after', 'Add After'),
        ('skip', 'Skip Departments'),
        ('replace', 'Replace Workflow'),
    ]
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        unique=True,
        help_text="Request category"
    )
    modifier_type = models.CharField(
        max_length=20,
        choices=MODIFIER_TYPE_CHOICES,
        default='add_front',
        help_text="Type of modification to apply"
    )
    departments_to_add = models.JSONField(
        default=list,
        blank=True,
        help_text="Departments to add (for add_front, add_after)"
    )
    departments_to_skip = models.JSONField(
        default=list,
        blank=True,
        help_text="Departments to skip (for skip modifier)"
    )
    apply_to_request_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Which request types this modifier applies to (empty = all)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this modifier is active"
    )
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority modifiers are applied first"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'category']
        verbose_name = 'Category Workflow Modifier'
        verbose_name_plural = 'Category Workflow Modifiers'

    def __str__(self):
        return f"{self.category} - {self.modifier_type}"
