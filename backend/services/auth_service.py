# File Location: backend/services/auth_service.py
# CRITICAL: Enhanced authentication with session management and security features

import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import secrets
import jwt
from passlib.context import CryptContext

from ..config import settings
from .database_service import DatabaseService
from .audit_service import AuditService
from .redis_client import RedisClient

logger = logging.getLogger(__name__)

class AuthenticationService:
    def __init__(self):
        self.db_service = DatabaseService()
        self.audit_service = AuditService()
        self.redis_client = RedisClient()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(hours=1)
        
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CRITICAL: Authenticate user with comprehensive security checks
        """
        try:
            # Step 1: Input validation
            if not email or not password:
                return {
                    "success": False,
                    "message": "Email and password are required",
                    "user_id": None,
                    "access_token": None
                }
            
            email = email.strip().lower()
            
            # Step 2: Get user profile
            user_profile = await self._get_user_by_email(email)
            
            if not user_profile:
                # Log failed attempt without revealing user existence
                await self.audit_service.log_event(
                    user_id="unknown",
                    event_type="login_attempt_invalid_email",
                    details={
                        "email": email,
                        "ip_address": ip_address,
                        "user_agent": user_agent
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Simulate processing time to prevent timing attacks
                await asyncio.sleep(0.5)
                
                return {
                    "success": False,
                    "message": "Invalid email or password",
                    "user_id": None,
                    "access_token": None
                }
            
            user_id = user_profile["id"]
            
            # Step 3: Check account lockout
            if await self._is_account_locked(user_id):
                await self.audit_service.log_event(
                    user_id=user_id,
                    event_type="login_attempt_locked_account",
                    details={
                        "email": email,
                        "ip_address": ip_address,
                        "user_agent": user_agent
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                return {
                    "success": False,
                    "message": "Account temporarily locked due to multiple failed attempts",
                    "user_id": user_id,
                    "access_token": None,
                    "locked_until": user_profile.get("account_locked_until")
                }
            
            # Step 4: Verify password
            if not self._verify_password(password, user_profile.get("password_hash", "")):
                # Increment failed attempts
                await self._handle_failed_login(user_id, email, ip_address, user_agent)
                
                return {
                    "success": False,
                    "message": "Invalid email or password",
                    "user_id": user_id,
                    "access_token": None
                }
            
            # Step 5: Check if account is active
            if not user_profile.get("is_active", True):
                await self.audit_service.log_event(
                    user_id=user_id,
                    event_type="login_attempt_inactive_account",
                    details={
                        "email": email,
                        "ip_address": ip_address,
                        "user_agent": user_agent
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                return {
                    "success": False,
                    "message": "Account is inactive. Please contact support.",
                    "user_id": user_id,
                    "access_token": None
                }
            
            # Step 6: Generate access token and session
            access_token = await self._generate_access_token(user_id, user_profile)
            session_id = await self._create_user_session(user_id, ip_address, user_agent)
            
            # Step 7: Reset failed attempts and update last login
            await self._handle_successful_login(user_id, ip_address, user_agent, session_id)
            
            # Step 8: Log successful authentication
            await self.audit_service.log_event(
                user_id=user_id,
                event_type="login_successful",
                details={
                    "email": email,
                    "session_id": session_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return {
                "success": True,
                "message": "Authentication successful",
                "user_id": user_id,
                "access_token": access_token,
                "session_id": session_id,
                "user_profile": {
                    "id": user_id,
                    "email": user_profile["email"],
                    "first_name": user_profile.get("first_name"),
                    "last_name": user_profile.get("last_name"),
                    "kyc_status": user_profile.get("kyc_status", "not_started"),
                    "kyc_level": user_profile.get("kyc_level", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Authentication error for email {email}: {str(e)}")
            
            return {
                "success": False,
                "message": "Authentication service unavailable",
                "user_id": None,
                "access_token": None
            }
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        CRITICAL: Validate JWT token with comprehensive checks
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            session_id = payload.get("session_id")
            
            if not user_id or not session_id:
                return {"valid": False, "user_id": None, "error": "Invalid token payload"}
            
            # Check if session is still active
            session_active = await self._is_session_active(session_id, user_id)
            
            if not session_active:
                return {"valid": False, "user_id": user_id, "error": "Session expired"}
            
            # Get current user profile
            user_profile = await self.db_service.get_user_profile(user_id)
            
            if not user_profile:
                return {"valid": False, "user_id": user_id, "error": "User not found"}
            
            if not user_profile.get("is_active", True):
                return {"valid": False, "user_id": user_id, "error": "Account inactive"}
            
            # Update session last activity
            await self._update_session_activity(session_id)
            
            return {
                "valid": True,
                "user_id": user_id,
                "session_id": session_id,
                "user_profile": user_profile
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "user_id": None, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "user_id": None, "error": "Invalid token"}
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return {"valid": False, "user_id": None, "error": "Token validation failed"}
    
    async def logout_user(
        self, 
        user_id: str, 
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        CRITICAL: Secure user logout with session cleanup
        """
        try:
            # Invalidate session in Redis
            await self.redis_client.delete(f"session:{session_id}")
            
            # Log session in database
            await self.db_service.create_audit_log(
                user_id=user_id,
                event_type="logout",
                details={
                    "session_id": session_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Logout error for user {user_id}: {str(e)}")
            return False
    
    async def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user profile by email with password hash"""
        try:
            query = """
                SELECT 
                    id, email, password_hash, first_name, last_name,
                    kyc_status, kyc_level, is_active, created_at,
                    failed_login_attempts, account_locked_until,
                    last_login_at
                FROM user_profiles 
                WHERE email = $1
            """
            
            result = await self.db_service.execute_with_retry(query, email)
            
            if result:
                row = result[0]
                return {
                    "id": str(row["id"]),
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "kyc_status": row["kyc_status"],
                    "kyc_level": row["kyc_level"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "failed_login_attempts": row["failed_login_attempts"],
                    "account_locked_until": row["account_locked_until"],
                    "last_login_at": row["last_login_at"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    async def _is_account_locked(self, user_id: str) -> bool:
        """Check if user account is currently locked"""
        try:
            user_profile = await self.db_service.get_user_profile(user_id)
            
            if not user_profile:
                return True  # Treat missing user as locked
            
            locked_until = user_profile.get("account_locked_until")
            
            if locked_until and isinstance(locked_until, str):
                locked_until = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
                return datetime.utcnow() < locked_until.replace(tzinfo=None)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking account lock status for user {user_id}: {str(e)}")
            return True  # Fail safe - treat as locked on error
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return self.pwd_context.verify(password, password_hash)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Hash password for storage"""
        return self.pwd_context.hash(password)
    
    async def _generate_access_token(self, user_id: str, user_profile: Dict[str, Any]) -> str:
        """Generate JWT access token"""
        try:
            session_id = secrets.token_urlsafe(32)
            
            payload = {
                "sub": user_id,
                "email": user_profile["email"],
                "session_id": session_id,
                "kyc_status": user_profile.get("kyc_status", "not_started"),
                "kyc_level": user_profile.get("kyc_level", 0),
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=24)
            }
            
            token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            return token
            
        except Exception as e:
            logger.error(f"Token generation error for user {user_id}: {str(e)}")
            raise
    
    async def _create_user_session(
        self, 
        user_id: str, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create user session in Redis"""
        try:
            session_id = secrets.token_urlsafe(32)
            
            session_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            # Store session in Redis with 24 hour expiration
            await self.redis_client.setex(
                f"session:{session_id}",
                86400,  # 24 hours
                session_data
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation error for user {user_id}: {str(e)}")
            raise
    
    async def _is_session_active(self, session_id: str, user_id: str) -> bool:
        """Check if session is active in Redis"""
        try:
            session_data = await self.redis_client.get(f"session:{session_id}")
            
            if not session_data:
                return False
            
            # Verify session belongs to the correct user
            if session_data.get("user_id") != user_id:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            return False
    
    async def _update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        try:
            session_data = await self.redis_client.get(f"session:{session_id}")
            
            if session_data:
                session_data["last_activity"] = datetime.utcnow().isoformat()
                
                await self.redis_client.setex(
                    f"session:{session_id}",
                    86400,  # Reset 24 hour expiration
                    session_data
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Session activity update error: {str(e)}")
            return False
    
    async def _handle_failed_login(
        self, 
        user_id: str, 
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Handle failed login attempt with lockout logic"""
        try:
            # Get current failed attempts
            user_profile = await self.db_service.get_user_profile(user_id)
            current_attempts = user_profile.get("failed_login_attempts", 0) + 1
            
            # Determine if account should be locked
            account_locked_until = None
            if current_attempts >= self.max_failed_attempts:
                account_locked_until = datetime.utcnow() + self.lockout_duration
            
            # Update user profile
            await self.db_service.execute_with_retry(
                """
                UPDATE user_profiles 
                SET 
                    failed_login_attempts = $1,
                    account_locked_until = $2,
                    updated_at = $3
                WHERE id = $4
                """,
                current_attempts,
                account_locked_until,
                datetime.utcnow(),
                user_id
            )
            
            # Log failed attempt
            await self.audit_service.log_event(
                user_id=user_id,
                event_type="login_failed",
                details={
                    "email": email,
                    "failed_attempts": current_attempts,
                    "account_locked": account_locked_until is not None,
                    "locked_until": account_locked_until.isoformat() if account_locked_until else None,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        except Exception as e:
            logger.error(f"Error handling failed login for user {user_id}: {str(e)}")
    
    async def _handle_successful_login(
        self, 
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Handle successful login - reset failed attempts and update last login"""
        try:
            await self.db_service.execute_with_retry(
                """
                UPDATE user_profiles 
                SET 
                    failed_login_attempts = 0,
                    account_locked_until = NULL,
                    last_login_at = $1,
                    updated_at = $1
                WHERE id = $2
                """,
                datetime.utcnow(),
                user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling successful login for user {user_id}: {str(e)}")