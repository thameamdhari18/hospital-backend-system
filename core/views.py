"""
Hospital Workflow System - Views
Comprehensive backend with error handling, validation, transactions, logging, and security
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib import messages
from django.utils import timezone
from django.core.validators import validate_email, MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import Request, Department, RequestHistory
from .services import auto_route, get_wait_time_analytics, get_department_wait_times, get_request_progress

# Configure logging
logger = logging.getLogger(__name__)


def dashboard(request):
    """
    Display dashboard with all requests, departments, and analytics
    """
    try:
        # Fetch all data with optimized queries
        requests = Request.objects.select_related('assigned_department').all()
        departments = Department.objects.all()

        # Overload detection - departments where current_load exceeds threshold
        overloaded = [d for d in departments if d.current_load > d.threshold]

        # Emergency count
        emergency_count = requests.filter(priority="Emergency").count()

        # Chart data
        dept_names = [d.name for d in departments]
        dept_loads = [d.current_load for d in departments]

        # SLA breached count
        sla_breached_count = sum(1 for r in requests if r.is_sla_breached)
        
        # Escalated count
        escalated_count = requests.filter(is_escalated=True).count()

        # Wait Time Analytics
        wait_analytics = get_wait_time_analytics()
        department_wait_times = get_department_wait_times()
        
        # Add progress info to each request
        requests_with_progress = []
        for req in requests:
            progress = get_request_progress(req)
            requests_with_progress.append({
                'request': req,
                'progress': progress
            })

        logger.info(f"Dashboard loaded - {requests.count()} requests, {departments.count()} departments")

        return render(request, "dashboard.html", {
            "requests": requests,
            "requests_with_progress": requests_with_progress,
            "departments": departments,
            "overloaded": overloaded,
            "dept_names": dept_names,
            "dept_loads": dept_loads,
            "emergency_count": emergency_count,
            "sla_breached_count": sla_breached_count,
            "escalated_count": escalated_count,
            "wait_analytics": wait_analytics,
            "department_wait_times": department_wait_times,
        })

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        messages.error(request, "Error loading dashboard. Please try again.")
        return render(request, "dashboard.html", {
            "requests": [],
            "requests_with_progress": [],
            "departments": [],
            "overloaded": [],
            "dept_names": [],
            "dept_loads": [],
            "emergency_count": 0,
            "sla_breached_count": 0,
            "escalated_count": 0,
            "wait_analytics": {},
            "department_wait_times": {},
        })


def request_timeline(request, request_id):
    """Display timeline/history for a specific request"""
    req = get_object_or_404(Request, id=request_id)
    history = RequestHistory.objects.filter(request=req).order_by("timestamp")
    
    # Get progress info
    progress = get_request_progress(req)

    return render(request, "timeline.html", {
        "request_obj": req,
        "history": history,
        "progress": progress,
    })


def create_request(request):
    """
    Create a new patient request with validation and atomic transactions
    """
    if request.method == "POST":
        try:
            # Extract and validate form data
            patient_name = request.POST.get("patient_name", "").strip()
            request_type = request.POST.get("request_type", "").strip()
            priority = request.POST.get("priority", "").strip()
            category = request.POST.get("category", "Outpatient").strip()

            # Validate patient name
            if not patient_name:
                messages.error(request, "Patient name is required.")
                return redirect("create_request")
            
            if len(patient_name) < 2:
                messages.error(request, "Patient name must be at least 2 characters.")
                return redirect("create_request")
            
            if len(patient_name) > 100:
                messages.error(request, "Patient name must be less than 100 characters.")
                return redirect("create_request")

            # Validate request type
            valid_request_types = [
                "MRI", "X-Ray", "CT Scan", "Ultrasound",
                "Cardiac", "ECG", "Blood Test", "Surgery",
                "General Checkup", "Dental", "Eye", "Optical",
                "Physiotherapy", "Vaccination"
            ]
            if request_type not in valid_request_types:
                messages.error(request, "Invalid request type selected.")
                return redirect("create_request")

            # Validate priority
            valid_priorities = ["Normal", "Emergency"]
            if priority not in valid_priorities:
                messages.error(request, "Invalid priority selected.")
                return redirect("create_request")
            
            # Validate category
            valid_categories = ["Outpatient", "Inpatient", "Emergency", "Follow-up"]
            if category not in valid_categories:
                category = "Outpatient"

            # Auto routing logic - now includes category
            department = auto_route(request_type, priority, category)

            if not department:
                logger.error(f"Failed to route request type: {request_type}")
                messages.error(request, "Failed to route request. Department not found.")
                return redirect("create_request")

            # Calculate queue position and estimated wait time
            pending_count = Request.objects.filter(
                assigned_department=department,
                status__in=['Assigned', 'In Progress']
            ).count()
            estimated_wait = (pending_count + 1) * 15
            
            # Calculate SLA deadline based on priority (emergency = shorter)
            base_sla_hours = getattr(department, 'sla_hours', 24)
            sla_hours = base_sla_hours if priority == "Normal" else min(base_sla_hours, 4)
            sla_deadline = timezone.now() + timedelta(hours=sla_hours)

            # Use atomic transaction for data consistency
            with transaction.atomic():
                new_request = Request.objects.create(
                    patient_name=patient_name,
                    request_type=request_type,
                    priority=priority,
                    category=category,
                    assigned_department=department,
                    status="Assigned",
                    queue_position=pending_count + 1,
                    estimated_wait_time=estimated_wait,
                    assigned_at=timezone.now(),
                    sla_deadline=sla_deadline
                )

                department.current_load += 1
                department.save()

                RequestHistory.objects.create(
                    request=new_request,
                    department=department,
                    status=f"Request Created - Queue Position: {pending_count + 1}, Est. Wait: {estimated_wait}min"
                )

            logger.info(f"New request created: {new_request.id} - {patient_name} - {request_type}")
            messages.success(request, f"Request created for {patient_name} (Queue: #{pending_count + 1}, Wait: ~{estimated_wait}min)")
            return redirect("dashboard")

        except Department.DoesNotExist:
            logger.error("Department not found in database")
            messages.error(request, "Department configuration error. Please contact administrator.")
            return redirect("create_request")

        except Exception as e:
            logger.error(f"Error creating request: {str(e)}")
            messages.error(request, "Error creating request. Please try again.")
            return redirect("create_request")

    return render(request, "create_request.html")


def update_status(request, request_id):
    """
    Update request status with validation and atomic transactions
    """
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("dashboard")

    try:
        req = get_object_or_404(Request, id=request_id)
        new_status = request.POST.get("status", "").strip()

        valid_statuses = ["Assigned", "In Progress", "Completed", "Closed"]
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect("dashboard")

        with transaction.atomic():
            old_status = req.status
            old_department = req.assigned_department

            req.status = new_status
            
            # Track time when status changes to In Progress
            if new_status == "In Progress" and not req.in_progress_at:
                req.in_progress_at = timezone.now()
            
            # Track time when status changes to Completed
            if new_status == "Completed" and not req.completed_at:
                req.completed_at = timezone.now()
            
            req.save()

            RequestHistory.objects.create(
                request=req,
                department=req.assigned_department,
                status=f"Status changed: {old_status} -> {new_status}"
            )

            logger.info(f"Request {req.id} status updated: {old_status} -> {new_status}")

            # If completed -> transfer to Billing
            if new_status == "Completed":
                current_dept = req.assigned_department

                if current_dept:
                    if current_dept.current_load > 0:
                        current_dept.current_load -= 1
                        current_dept.save()

                next_dept = Department.objects.filter(name__iexact="Billing").first()

                if next_dept:
                    # Calculate new queue position for Billing department
                    billing_pending = Request.objects.filter(
                        assigned_department=next_dept,
                        status__in=['Assigned', 'In Progress']
                    ).exclude(id=req.id).count()
                    
                    req.assigned_department = next_dept
                    req.status = "Assigned"
                    req.queue_position = billing_pending + 1
                    req.assigned_at = timezone.now()
                    req.save()

                    next_dept.current_load += 1
                    next_dept.save()

                    RequestHistory.objects.create(
                        request=req,
                        department=next_dept,
                        status=f"Transferred to Billing (Queue: #{billing_pending + 1})"
                    )
                    
                    logger.info(f"Request {req.id} transferred to Billing department")
                else:
                    logger.warning(f"Billing department not found for request {req.id}")

            # If closed -> reduce department load
            elif new_status == "Closed":
                current_dept = req.assigned_department
                if current_dept:
                    if current_dept.current_load > 0:
                        current_dept.current_load -= 1
                        current_dept.save()
                        logger.info(f"Department {current_dept.name} load decreased to {current_dept.current_load}")

            messages.success(request, f"Status updated to {new_status}")

    except Request.DoesNotExist:
        logger.error(f"Request {request_id} not found")
        messages.error(request, "Request not found.")
        
    except Exception as e:
        logger.error(f"Error updating status for request {request_id}: {str(e)}")
        messages.error(request, "Error updating status. Please try again.")

    return redirect("dashboard")

