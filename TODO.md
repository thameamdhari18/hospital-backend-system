# TODO - Request Categories for Different Workflow Paths - COMPLETED

## Summary
Implemented category-based workflow paths so that requests follow different paths based on their category (Outpatient, Inpatient, Emergency, Follow-up).

## Completed Tasks

### 1. Updated core/models.py
- [x] Added WorkflowDefinition model with request_type, workflow_steps (JSONField), initial_department
- [x] Added CategoryWorkflowModifier model with category, modifier_type, departments_to_add, departments_to_skip

### 2. Updated core/admin.py
- [x] Registered WorkflowDefinition model with admin interface
- [x] Registered CategoryWorkflowModifier model with admin interface
- [x] Added list_editable for Request model (category, priority, status, etc.)

### 3. Database Migration
- [x] Created migration 0004_add_workflow_models
- [x] Applied migration successfully

### 4. Updated core/services.py
- [x] Added BASE_WORKFLOWS dictionary for request type workflows
- [x] Added CATEGORY_WORKFLOWS dictionary for category modifiers
- [x] Created get_workflow() function combining request_type + category
- [x] Updated auto_route() to route based on category (Emergency→Emergency dept, Inpatient→Admission, etc.)

### 5. Updated core/views.py
- [x] create_request already passes category to auto_route

### 6. Updated core/templates/dashboard.html
- [x] Added Category column with color-coded badges

### 7. Management Command
- [x] Created seed_workflows command to populate initial data
- [x] Executed seed - 14 workflow definitions + 4 category modifiers

## Workflow Paths by Category

| Category | Behavior |
|----------|----------|
| Outpatient | Standard workflow (Reception → Treatment → Billing) |
| Emergency | Routes through Emergency department first |
| Inpatient | Routes through Admission first, adds ICU for Surgery/Cardiac |
| Follow-up | Skips Reception, goes directly to treatment department |

## Admin Interface
Access Django admin to manage workflows:
- /admin/core/workflowdefinition/ - Configure workflow steps per request type
- /admin/core/categoryworkflowmodifier/ - Configure category-based modifications
