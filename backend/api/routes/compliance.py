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
    category: str = Form(...),
    document_type: str = Form(...),
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Upload document - FIXED with proper error handling"""
    try:
        user_id = current_user['id']
        logger.info(f"Upload attempt by {user_id}, file: {file.filename}")

        # 1. VALIDATE INPUTS FIRST
        if not category or not document_type:
            raise HTTPException(400, "Category and document_type are required")

        # 2. READ FILE
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(400, "File is empty")

        # 3. UPLOAD TO STORAGE (with verification)
        file_path = f"{user_id}/{category}/{uuid.uuid4()}_{file.filename}"
        
        try:
            # THIS IS THE CRITICAL LINE - must match your bucket name
            upload_response = supabase.storage.from_("compliance-documents").upload(
                path=file_path,
                file=file_bytes
            )
            
            # Check if upload actually succeeded
            if hasattr(upload_response, 'error') and upload_response.error:
                raise HTTPException(500, f"Storage upload failed: {upload_response.error}")
                
        except Exception as storage_error:
            logger.error(f"Storage upload crashed: {str(storage_error)}")
            # Provide a helpful error message
            raise HTTPException(500, f"Failed to upload to storage. Check bucket 'compliance-documents' exists and has public policies. Error: {str(storage_error)[:100]}")

        # 4. GET PUBLIC URL
        try:
            file_url = supabase.storage.from_("compliance-documents").get_public_url(file_path)
        except Exception as url_error:
            logger.error(f"Failed to get URL: {url_error}")
            # Construct a fallback URL
            project_ref = "YOUR_PROJECT_REF"  # Get from Supabase settings
            file_url = f"https://{project_ref}.supabase.co/storage/v1/object/public/compliance-documents/{file_path}"

        # 5. SAVE TO DATABASE (ONLY if upload succeeded)
        doc_data = {
            "user_id": user_id,
            "category": category,
            "document_type": document_type,
            "file_name": file.filename,
            "file_url": file_url,
            "file_size": len(file_bytes),
            "mime_type": file.content_type,
            "uploaded_by": user_id,
            "verification_status": "pending",
            "storage_path": file_path  # Crucial for debugging!
        }

        db_result = supabase.table("compliance_documents").insert(doc_data).execute()
        
        # ... inside your upload function, after try:
        logger.info(f"=== STORAGE DEBUG ===")
        logger.info(f"Supabase client configured? {'yes' if supabase else 'no'}")
        # List all buckets to see what's available
        try:
            buckets_response = supabase.storage.list_buckets()
            logger.info(f"Available buckets from API: {buckets_response}")
        except Exception as bucket_list_error:
            logger.error(f"Failed to list buckets: {bucket_list_error}")
            
        # Verify database insert
        if not db_result.data:
            logger.error("Database insert returned no data")
            # Attempt to clean up the uploaded file since DB failed
            try:
                supabase.storage.from_("compliance-documents").remove([file_path])
            except:
                pass
            raise HTTPException(500, "Failed to save document record to database")

        logger.info(f"✅ SUCCESS: User {user_id} uploaded {file.filename}, record ID: {db_result.data[0]['id']}")

        return {
            "success": True,
            "document_id": db_result.data[0]['id'],
            "file_url": file_url,
            "message": "Document fully processed and saved"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected upload error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Upload process failed: {str(e)[:150]}")

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