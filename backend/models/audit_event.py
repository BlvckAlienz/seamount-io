# backend/models/audit_event.py
from enum import Enum

class AuditEventType(str, Enum):
    # User events
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_PROFILE_UPDATED = "user_profile_updated"
    
    # Compliance events
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    CHECKLIST_ITEM_COMPLETED = "checklist_item_completed"
    CHECKLIST_ITEM_INCOMPLETED = "checklist_item_incompleted"
    
    # Tax events
    TAX_CALCULATION = "tax_calculation"
    TAX_EXEMPTION_CHECK = "tax_exemption_check"
    TAX_PENALTY_EST = "tax_penalty_est"
    TAX_SCENARIO_MODELED = "tax_scenario_modeled"
    TAX_PROFILE_UPDATED = "tax_profile_updated"
    
    # Subscription events
    SUBSCRIPTION_INITIATED = "subscription_initiated"
    SUBSCRIPTION_COMPLETED = "subscription_completed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    
    # System events
    SYSTEM_SYNC = "system_sync"
    SYSTEM_ERROR = "system_error"