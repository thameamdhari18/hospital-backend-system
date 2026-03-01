"""
Hospital Workflow System - Services
Business logic with workflow engine, validation, workload tracking, and logging
"""

import logging
from django.db import transaction
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from .models import Department, Request, RequestHistory, WorkflowDefinition, CategoryWorkflowModifier

logger = logging.getLogger(__name__)

# -----------------------------
# WORKFLOW DEFINITIONS (Base - by Request Type)
# -----------------------------

BASE_WORKFLOWS = {
    # Radiology
    "MRI": ["Reception", "Radiology", "Billing"],
    "X-Ray": ["Reception", "Radiology", "Billing"],
    "CT Scan": ["Reception", "Radiology", "Billing"],
    "Ultrasound": ["Reception", "Radiology", "Billing"],
    # Cardiology
    "Cardiac": ["Reception", "Cardiology", "ICU", "Billing"],
    "ECG": ["Reception", "Cardiology", "Billing"],
    # Pathology
    "Blood Test": ["Reception", "Pathology", "Billing"],
    # Surgery
    "Surgery": ["Reception", "Surgery", "ICU", "Billing"],
    # General Medicine
    "General Checkup": ["Reception", "General Medicine", "Billing"],
    # Dental
    "Dental": ["Reception", "Dental", "Billing"],
    # Ophthalmology
    "Eye": ["Reception", "Ophthalmology", "Billing"],
    "Optical": ["Reception", "Ophthalmology", "Billing"],
    # Physiotherapy
    "Physiotherapy": ["Reception", "Physiotherapy", "Billing"],
    # Pharmacy
    "Vaccination": ["Reception", "Pharmacy", "Billing"],
}

# -----------------------------
# CATEGORY-BASED WORKFLOW MODIFIERS
# -----------------------------
# These modify the base workflow based on category

CATEGORY_WORKFLOWS = {
    # Emergency category - always starts with Emergency department
    "Emergency": {
        "modifier": "emergency",
        "add_front": ["Emergency"],
    },
    # Inpatient category - adds Admission at start and potentially ICU
    "Inpatient": {
        "modifier": "inpatient", 
        "add_front": ["Admission"],
        "add_after": {
            "Surgery": ["ICU"],
            "Cardiac": ["ICU"],
        },
    },
    # Outpatient category - standard workflow (default)
    "Outpatient": {
        "modifier": "outpatient",
    },
    # Follow-up category - shorter path, may skip some departments
    "Follow-up": {
        "modifier": "followup",
        "skip_departments": ["Reception"],
    },
}


def get_workflow(request_type, category="Outpatient"):
    """
    Get workflow path based on request type and category.
    Combines base workflow with category-specific modifications.
    """
    # Get base workflow for request type
    base_workflow = list(BASE_WORKFLOWS.get(request_type, ["Reception", "Billing"]))
    
    # Get category modifier
    category_mod = CATEGORY_WORKFLOWS.get(category, CATEGORY_WORKFLOWS["Outpatient"])
    
    workflow = base_workflow.copy()
    
    # Apply "skip_departments" for Follow-up
    if "skip_departments" in category_mod:
        workflow = [d for d in workflow if d not in category_mod["skip_departments"]]
    
    # Apply "add_front" for Emergency/Inpatient
    if "add_front" in category_mod:
        # Add front departments (excluding ones already in workflow)
        for dept in category_mod["add_front"]:
            if dept not in workflow:
                workflow.insert(0, dept)
    
    # Apply "add_after" for Inpatient
    if "add_after" in category_mod:
        # For specific request types, add departments after current dept
        if request_type in category_mod["add_after"]:
            for add_dept in category_mod["add_after"][request_type]:
                # Find position of key departments to insert after
                key_depts = ["Surgery", "Cardiology", "Surgery"]
                for key_dept in key_depts:
                    if key_dept in workflow:
                        idx = workflow.index(key_dept)
                        if add_dept not in workflow:
                            workflow.insert(idx + 1, add_dept)
                        break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_workflow = []
    for d in workflow:
        if d not in seen:
            seen.add(d)
            unique_workflow.append(d)
    
    return unique_workflow


# Alias for backward compatibility
WORKFLOWS = BASE_WORKFLOWS


# -----------------------------
# REQUEST TYPE TO DEPARTMENT MAPPING
# -----------------------------

REQUEST_TYPE_MAPPING = {
    # Radiology
    "MRI": "Radiology",
    "X-Ray": "Radiology",
    "CT Scan": "Radiology",
    "Ultrasound": "Radiology",
    # Cardiology
    "Cardiac": "Cardiology",
    "ECG": "Cardiology",
    # Pathology
    "Blood Test": "Pathology",
    # Surgery
    "Surgery": "Surgery",
    # General Medicine
    "General Checkup": "General Medicine",
    # Dental
    "Dental": "Dental",
    # Ophthalmology
    "Eye": "Ophthalmology",
    "Optical": "Ophthalmology",
    # Physiotherapy
    "Physiotherapy": "Physiotherapy",
    # Pharmacy
    "Vaccination": "Pharmacy",
}


# -----------------------------
# AUTO ROUTING
# -----------------------------

def auto_route(request_type, priority, category="Outpatient"):
    """
    Route request to initial department.
    Emergency and category-specific routing overrides normal routing.
    """

    try:
        # Emergency priority takes precedence
        if priority == "Emergency":
            emergency_dept = Department.objects.filter(name="Emergency").first()
            if emergency_dept:
                return emergency_dept
            return Department.objects.get(name="Reception")

        # Category-based routing
        if category == "Emergency":
            # Emergency category routes through Emergency department first
            emergency_dept = Department.objects.filter(name="Emergency").first()
            if emergency_dept:
                return emergency_dept
        
        elif category == "Inpatient":
            # Inpatient category routes through Admission first
            admission_dept = Department.objects.filter(name="Admission").first()
            if admission_dept:
                return admission_dept
        
        elif category == "Follow-up":
            # Follow-up skips Reception, goes directly to treatment department
            pass  # Use standard mapping
        
        # Default: use request type mapping
        dept_name = REQUEST_TYPE_MAPPING.get(request_type)

        if not dept_name:
            logger.warning(f"No mapping found for {request_type}, defaulting to Reception")
            dept_name = "Reception"

        return Department.objects.get(name=dept_name)

    except Department.DoesNotExist:
        logger.error(f"Department {dept_name} not found in database")
        # Fallback to Reception
        return Department.objects.filter(name="Reception").first()


# -----------------------------
# WORKFLOW ENGINE
# -----------------------------

@transaction.atomic
def process_workflow_transition(req, new_status):
    """
    Core workflow processor.
    Handles:
    - Status update
    - Department transfer
    - Load balancing
    - Movement logging
    """

    try:
        old_status = req.status
        old_department = req.assigned_department

        # Update status
        req.status = new_status
        req.save()

        RequestHistory.objects.create(
            request=req,
            department=old_department,
            status=f"{old_status} -> {new_status}"
        )

        logger.info(f"Request {req.id} status updated: {old_status} -> {new_status}")

        # Only transfer when Completed
        if new_status != "Completed":
            return True

        workflow = WORKFLOWS.get(req.request_type)

        if not workflow:
            logger.warning(f"No workflow defined for {req.request_type}")
            return False

        if not old_department:
            logger.warning(f"Request {req.id} has no assigned department")
            return False

        current_dept_name = old_department.name

        if current_dept_name not in workflow:
            logger.warning(f"{current_dept_name} not in workflow for {req.request_type}")
            return False

        current_index = workflow.index(current_dept_name)

        # Move to next department if exists
        if current_index + 1 < len(workflow):

            next_dept_name = workflow[current_index + 1]
            next_dept = Department.objects.filter(name=next_dept_name).first()

            if not next_dept:
                logger.error(f"Next department {next_dept_name} not found")
                return False

            # Decrease current department load
            if old_department.current_load > 0:
                old_department.current_load -= 1
                old_department.save()

            # Assign next department
            req.assigned_department = next_dept
            req.status = "Assigned"
            req.save()

            # Increase next department load
            next_dept.current_load += 1
            next_dept.save()

            # Log transfer
            RequestHistory.objects.create(
                request=req,
                department=next_dept,
                status=f"Transferred to {next_dept.name}"
            )

            logger.info(
                f"Request {req.id} moved from {current_dept_name} -> {next_dept.name}"
            )

        return True

    except Exception as e:
        logger.error(f"Workflow transition failed for request {req.id}: {str(e)}")
        raise


# -----------------------------
# WORKLOAD ANALYTICS
# -----------------------------

def get_department_workload_stats():
    """
    Returns workload statistics for dashboard analytics.
    """

    stats = {}

    for dept in Department.objects.all():
        utilization = (
            (dept.current_load / dept.threshold) * 100
            if dept.threshold > 0 else 0
        )

        stats[dept.name] = {
            "current_load": dept.current_load,
            "threshold": dept.threshold,
            "available_capacity": max(0, dept.threshold - dept.current_load),
            "is_overloaded": dept.current_load > dept.threshold,
            "utilization_percent": round(utilization, 2),
        }

    return stats


# -----------------------------
# WAIT TIME ANALYTICS
# -----------------------------

def get_wait_time_analytics():
    """
    Calculate wait time analytics for all requests.
    Returns various metrics for progress tracking.
    """
    
    now = timezone.now()
    
    # Get all requests
    all_requests = Request.objects.all()
    completed_requests = Request.objects.filter(status='Closed')
    pending_requests = Request.objects.filter(status__in=['Assigned', 'In Progress'])
    
    # Calculate average wait times
    analytics = {
        # Overall stats
        'total_requests': all_requests.count(),
        'completed_requests': completed_requests.count(),
        'pending_requests': pending_requests.count(),
        
        # Average wait time for pending requests
        'avg_wait_time_pending': 0,
        'max_wait_time_pending': 0,
        'min_wait_time_pending': 0,
        
        # Completed requests average processing time
        'avg_processing_time': 0,
        
        # By priority
        'emergency_pending': pending_requests.filter(priority='Emergency').count(),
        'normal_pending': pending_requests.filter(priority='Normal').count(),
        
        # By status
        'assigned_count': Request.objects.filter(status='Assigned').count(),
        'in_progress_count': Request.objects.filter(status='In Progress').count(),
        'completed_count': Request.objects.filter(status='Completed').count(),
        'closed_count': Request.objects.filter(status='Closed').count(),
    }
    
    # Calculate wait times for pending requests
    if pending_requests.exists():
        wait_times = []
        for req in pending_requests:
            if req.assigned_at:
                wait_seconds = (now - req.assigned_at).total_seconds()
                wait_times.append(wait_seconds / 60)  # Convert to minutes
        
        if wait_times:
            analytics['avg_wait_time_pending'] = round(sum(wait_times) / len(wait_times), 1)
            analytics['max_wait_time_pending'] = round(max(wait_times), 1)
            analytics['min_wait_time_pending'] = round(min(wait_times), 1)
    
    # Calculate average processing time for completed requests
    completed_with_times = completed_requests.exclude(
        Q(completed_at__isnull=True) | Q(created_at__isnull=True)
    )
    
    if completed_with_times.exists():
        processing_times = []
        for req in completed_with_times:
            if req.completed_at and req.created_at:
                process_seconds = (req.completed_at - req.created_at).total_seconds()
                processing_times.append(process_seconds / 60)  # Convert to minutes
        
        if processing_times:
            analytics['avg_processing_time'] = round(sum(processing_times) / len(processing_times), 1)
    
    return analytics


def get_department_wait_times():
    """
    Calculate average wait times by department.
    """
    
    now = timezone.now()
    dept_times = {}
    
    for dept in Department.objects.all():
        # Pending requests in this department
        pending = Request.objects.filter(
            assigned_department=dept,
            status__in=['Assigned', 'In Progress']
        )
        
        wait_times = []
        for req in pending:
            if req.assigned_at:
                wait_minutes = (now - req.assigned_at).total_seconds() / 60
                wait_times.append(wait_minutes)
        
        avg_wait = round(sum(wait_times) / len(wait_times), 1) if wait_times else 0
        
        dept_times[dept.name] = {
            'pending_count': pending.count(),
            'avg_wait_minutes': avg_wait,
            'max_wait': round(max(wait_times), 1) if wait_times else 0,
            'current_load': dept.current_load,
            'threshold': dept.threshold,
            'utilization': round((dept.current_load / dept.threshold * 100) if dept.threshold > 0 else 0, 1)
        }
    
    return dept_times


def get_request_progress(req):
    """
    Calculate the progress percentage for a specific request.
    Returns progress details including current stage and time spent.
    """
    
    if not req:
        return None
    
    now = timezone.now()
    
    # Determine workflow stages
    workflow = WORKFLOWS.get(req.request_type, [])
    
    if not workflow:
        # No workflow defined
        return {
            'stages': [],
            'current_stage': 0,
            'progress_percent': 0,
            'time_in_current_stage': 0,
            'total_time': 0,
        }
    
    # Calculate progress based on status
    status_progress = {
        'Assigned': 10,
        'In Progress': 50,
        'Completed': 90,
        'Closed': 100,
    }
    
    progress_percent = status_progress.get(req.status, 0)
    
    # Calculate current stage
    current_stage = 0
    if req.assigned_department:
        dept_name = req.assigned_department.name
        if dept_name in workflow:
            current_stage = workflow.index(dept_name) + 1
    
    # Time calculations
    time_in_current_stage = 0
    if req.assigned_at:
        time_in_current_stage = round((now - req.assigned_at).total_seconds() / 60, 1)
    
    total_time = 0
    if req.created_at:
        total_time = round((now - req.created_at).total_seconds() / 60, 1)
    
    return {
        'stages': workflow,
        'current_stage': current_stage,
        'progress_percent': progress_percent,
        'time_in_current_stage': time_in_current_stage,
        'total_time': total_time,
        'status': req.status,
        'assigned_department': req.assigned_department.name if req.assigned_department else None,
    }


# -----------------------------
# VALIDATION
# -----------------------------

def validate_request_data(patient_name, request_type, priority):
    """
    Validate request creation input.
    """

    errors = []

    if not patient_name or len(patient_name.strip()) < 2:
        errors.append("Patient name must be at least 2 characters")

    if request_type not in REQUEST_TYPE_MAPPING:
        errors.append("Invalid request type")

    if priority not in ["Normal", "Emergency"]:
        errors.append("Invalid priority")

    if errors:
        return False, "; ".join(errors)

    return True, None
