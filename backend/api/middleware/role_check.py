from fastapi import HTTPException, Depends
from supabase import Client
from ..auth import get_current_user

def require_role(required_role: str):
    def role_checker(
        current_user: dict = Depends(get_current_user),
        supabase: Client = Depends(get_supabase_client)
    ):
        user_profile = supabase.from_("user_profiles").select("role").eq("id", current_user["id"]).single().execute()
        
        if not user_profile.data or user_profile.data["role"] != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {required_role}. Your role: {user_profile.data.get('role', 'unknown')}"
            )
        
        return current_user
    
    return role_checker