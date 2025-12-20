# File Location: backend/api/routes/compliance.py
# 🚨 MISSION CRITICAL: Compliance & audit management - FIXED VERSION

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form  # ✅ Added Form import
from typing import Dict, Any, List
import logging
from datetime import datetime, timezone
import uuid

from backend.dependencies import get_supabase_client, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/checklist")
async def get_audit_checklist(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Get user's audit checklist - FIXED: Deduplicate items"""
    try:
        user_id = current_user['id']
        
        # Fetch all checklist items
        result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        # Handle no data case
        if not result.data or len(result.data) == 0:
            return {
                "success": True,
                "checklist": [],
                "checklist_by_category": {},
                "stats": {
                    "total_items": 0,
                    "completed_items": 0,
                    "completion_percentage": 0
                }
            }
        
        # ✅ DEDUPLICATION: Remove duplicates by creating a dictionary keyed by (category, item_description)
        seen_items = {}
        unique_items = []
        
        for item in result.data:
            # Create a unique key for this checklist item
            category = item.get('category', '')
            item_description = item.get('item_description', '')
            key = f"{category}_{item_description}"
            
            # Only add if we haven't seen this exact item before
            if key not in seen_items:
                seen_items[key] = True
                unique_items.append(item)
            else:
                # Log duplicate found (for debugging)
                logger.warning(f"Duplicate checklist item found for user {user_id}: {key}")
        
        # Sort items by category and item_code
        sorted_items = sorted(unique_items, key=lambda x: (
            x.get('category', ''), 
            x.get('item_code', '')
        ))
        
        # Group by category for the response
        checklist_by_category = {}
        for item in sorted_items:
            category = item.get('category', 'UNKNOWN')
            if category not in checklist_by_category:
                checklist_by_category[category] = []
            checklist_by_category[category].append(item)
        
        # Calculate completion stats based on DEDUPLICATED items
        total_items = len(sorted_items)
        completed_items = sum(1 for item in sorted_items if item.get('is_completed', False))
        completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
        
        return {
            "success": True,
            "checklist": sorted_items,
            "checklist_by_category": checklist_by_category,
            "stats": {
                "total_items": total_items,
                "completed_items": completed_items,
                "completion_percentage": round(completion_percentage, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"[Checklist Fetch] Error: {e}")
        # Return empty data instead of crashing
        return {
            "success": True,
            "checklist": [],
            "checklist_by_category": {},
            "stats": {
                "total_items": 0,
                "completed_items": 0,
                "completion_percentage": 0
            }
        }

@router.post("/checklist/{item_id}/complete")
async def mark_checklist_item_complete(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Mark checklist item as complete"""
    try:
        user_id = current_user['id']
        
        result = supabase.from_("audit_checklist_items")\
            .update({
                "is_completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": user_id
            })\
            .eq("id", item_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        
        return {
            "success": True,
            "message": "Checklist item marked as complete"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Checklist Update] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_compliance_documents(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Get all compliance documents for user"""
    try:
        user_id = current_user['id']
        
        result = supabase.from_("compliance_documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        # Group by category
        documents_by_category = {}
        for doc in (result.data or []):
            category = doc['category']
            if category not in documents_by_category:
                documents_by_category[category] = []
            documents_by_category[category].append(doc)
        
        return {
            "success": True,
            "documents": result.data or [],
            "documents_by_category": documents_by_category
        }
    except Exception as e:
        logger.error(f"[Documents Fetch] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload")
async def upload_compliance_document(
    file: UploadFile = File(...),
    category: str = Form(None),  # Make optional for debugging
    document_type: str = Form(None),  # Make optional for debugging
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Upload compliance document - DEBUG VERSION"""
    try:
        logger.info(f"📥 Upload endpoint called")
        logger.info(f"📤 File: {file.filename}, Category: {category}, Type: {document_type}")
        
        if not category or not document_type:
            logger.error(f"❌ Missing form data: category={category}, type={document_type}")
            raise HTTPException(status_code=400, detail="Category and document type are required")
        
        user_id = current_user['id']
        
        # Generate filename
        unique_filename = f"{user_id}/{category}/{uuid.uuid4().hex}_{file.filename}"
        
        # Read file
        content = await file.read()
        logger.info(f"📦 Read {len(content)} bytes")
        
        # Try simple upload
        try:
            result = supabase.storage.from_("compliance-documents") \
                .upload(unique_filename, content)
            
            if not result:
                raise Exception("Upload returned None")
                
        except Exception as e:
            logger.error(f"❌ Storage upload failed: {e}")
            # Try to list buckets to debug
            try:
                buckets = supabase.storage.list_buckets()
                logger.info(f"📊 Available buckets: {buckets}")
            except:
                logger.error("❌ Cannot list buckets")
            raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
        
        # Get URL
        file_url = supabase.storage.from_("compliance-documents") \
            .get_public_url(unique_filename)
        
        # Save to database
        doc_data = {
            "user_id": user_id,
            "category": category,
            "document_type": document_type,
            "file_name": file.filename,
            "file_url": file_url,
            "file_size": len(content),
            "uploaded_by": user_id
        }
        
        db_result = supabase.from_("compliance_documents") \
            .insert(doc_data) \
            .execute()
        
        return {
            "success": True,
            "message": "Upload successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exemption-checker")
async def check_tax_exemptions(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Tax exemption checker - rule-based system"""
    try:
        data = await request.json()
        user_id = current_user['id']
        
        # Extract form data
        business_type = data.get('business_type')
        annual_turnover = float(data.get('annual_turnover', 0))
        industry_sector = data.get('industry_sector')
        employee_count = int(data.get('employee_count', 0))
        
        # Simple rule-based exemption matching
        eligible_exemptions = []
        estimated_savings = 0
        
        # Rule 1: Small company exemption (₦100M turnover)
        if annual_turnover < 100_000_000:
            eligible_exemptions.append({
                "id": 20,
                "name": "Small Company 0% Tax",
                "description": "Companies with turnover below ₦100M pay 0% CIT",
                "estimated_savings": annual_turnover * 0.30
            })
            estimated_savings += annual_turnover * 0.30
        
        # Rule 2: Agricultural business
        if industry_sector == 'agriculture':
            eligible_exemptions.append({
                "id": 24,
                "name": "Agricultural Business Tax Holiday",
                "description": "5-year tax holiday for agricultural businesses",
                "estimated_savings": 0
            })
        
        # Rule 3: Minimum wage exemption
        if employee_count > 0:
            eligible_exemptions.append({
                "id": 1,
                "name": "Minimum Wage Workers Exempt",
                "description": "Employees earning minimum wage or less are exempt from PAYE",
                "estimated_savings": 0
            })
        
        # Rule 4: Pension contributions
        if data.get('has_pension_contributions'):
            eligible_exemptions.append({
                "id": 5,
                "name": "Pension Contribution Deduction",
                "description": "Pension contributions are tax-deductible",
                "estimated_savings": 0
            })
        
        # Save response
        response_data = {
            "user_id": user_id,
            "business_type": business_type,
            "annual_turnover": annual_turnover,
            "industry_sector": industry_sector,
            "employee_count": employee_count,
            "responses": data,
            "eligible_exemptions": eligible_exemptions,
            "estimated_tax_savings": estimated_savings,
            "report_generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.from_("tax_exemption_responses")\
            .insert(response_data)\
            .execute()
        
        logger.info(f"✅ Tax exemption check completed for user {user_id}: {len(eligible_exemptions)} exemptions found")
        
        return {
            "success": True,
            "eligible_exemptions": eligible_exemptions,
            "estimated_tax_savings": estimated_savings,
            "message": f"Found {len(eligible_exemptions)} exemptions you qualify for"
        }
        
    except Exception as e:
        logger.error(f"[Exemption Checker] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auditor-access/grant")
async def grant_auditor_access(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Grant auditor access to user's documents"""
    try:
        data = await request.json()
        user_id = current_user['id']
        
        auditor_email = data.get('auditor_email')
        auditor_name = data.get('auditor_name')
        
        if not auditor_email:
            raise HTTPException(status_code=400, detail="Auditor email required")
        
        # Grant access
        access_data = {
            "user_id": user_id,
            "auditor_email": auditor_email,
            "auditor_name": auditor_name,
            "is_active": True
        }
        
        result = supabase.from_("auditor_access")\
            .insert(access_data)\
            .execute()
        
        logger.info(f"✅ Auditor access granted: {auditor_email} for user {user_id}")
        
        return {
            "success": True,
            "message": f"Access granted to {auditor_email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auditor Access] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))