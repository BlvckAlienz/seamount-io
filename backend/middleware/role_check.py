# File Location: backend/middleware/role_check.py
from fastapi import HTTPException, Depends
from supabase import Client

def require_role(required_role: str):
    """
    Factory function that creates a role checking dependency.
    This avoids circular imports by not importing from main.py directly.
    """
    def role_checker(current_user: dict, supabase: Client):
        # Check if user has the required role
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=403, 
                detail=f"{required_role.capitalize()} role required"
            )
        return current_user
    return role_checker

# Note: We removed the get_supabase_client function as it's not needed here