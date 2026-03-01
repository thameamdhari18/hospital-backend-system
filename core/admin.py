"""
Hospital Workflow System - Admin Configuration
Django admin interface customization
"""

from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Department, Request, RequestHistory, WorkflowDefinition, CategoryWorkflowModifier


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin configuration for Department model"""
    list_display = ['name', 'current_load', 'threshold', 'is_overloaded', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['threshold', 'is_active']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Capacity Management', {
            'fields': ('current_load', 'threshold', 'sla_hours')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Admin configuration for Request model"""
    
    def sla_status(self, obj):
        """Display SLA status with color"""
        if obj.is_sla_breached:
            return mark_safe('<span style="color:red;font-weight:bold;">BREACHED</span>')
        elif obj.sla_deadline:
            return mark_safe('<span style="color:green;">OK</span>')
        return '-'
    sla_status.short_description = 'SLA'
    
    list_display = ['id', 'patient_name', 'request_type', 'category', 'priority', 'status', 'queue_position', 'assigned_department', 'sla_status', 'is_escalated', 'created_at']
    list_filter = ['status', 'priority', 'category', 'is_escalated', 'request_type', 'created_at']
    search_fields = ['patient_name', 'request_type', 'notes', 'escalation_reason']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['category', 'priority', 'status', 'queue_position', 'assigned_department', 'is_escalated']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name',)
        }),
        ('Request Details', {
            'fields': ('request_type', 'category', 'priority', 'status', 'assigned_department')
        }),
        ('Queue Management', {
            'fields': ('queue_position', 'estimated_wait_time')
        }),
        ('SLA & Escalation', {
            'fields': ('sla_deadline', 'is_escalated', 'escalation_reason')
        }),
        ('Timestamps', {
            'fields': ('assigned_at', 'in_progress_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
    )


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for RequestHistory model"""
    list_display = ['request', 'department', 'status', 'timestamp']
    list_filter = ['status', 'timestamp']
    search_fields = ['request__patient_name', 'status', 'notes']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request', 'department', 'status', 'notes')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowDefinition model"""
    list_display = ['request_type', 'workflow_steps_display', 'initial_department', 'is_active', 'updated_at']
    list_filter = ['is_active', 'request_type']
    list_editable = ['is_active', 'initial_department']
    search_fields = ['request_type', 'initial_department']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['request_type']
    
    def workflow_steps_display(self, obj):
        """Display workflow steps as string"""
        return ' → '.join(obj.workflow_steps) if obj.workflow_steps else '-'
    workflow_steps_display.short_description = 'Workflow Steps'
    
    fieldsets = (
        ('Request Type', {
            'fields': ('request_type', 'is_active')
        }),
        ('Workflow Configuration', {
            'fields': ('initial_department', 'workflow_steps')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CategoryWorkflowModifier)
class CategoryWorkflowModifierAdmin(admin.ModelAdmin):
    """Admin configuration for CategoryWorkflowModifier model"""
    list_display = ['category', 'modifier_type', 'departments_display', 'priority', 'is_active']
    list_filter = ['is_active', 'modifier_type', 'category']
    list_editable = ['modifier_type', 'is_active', 'priority']
    search_fields = ['category', 'departments_to_add', 'departments_to_skip']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-priority', 'category']
    
    def departments_display(self, obj):
        """Display departments as string"""
        if obj.modifier_type == 'skip':
            return ', '.join(obj.departments_to_skip) if obj.departments_to_skip else '-'
        return ', '.join(obj.departments_to_add) if obj.departments_to_add else '-'
    departments_display.short_description = 'Departments'
    
    fieldsets = (
        ('Category', {
            'fields': ('category', 'modifier_type', 'is_active', 'priority')
        }),
        ('Department Modifications', {
            'fields': ('departments_to_add', 'departments_to_skip', 'apply_to_request_types')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
