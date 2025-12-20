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

def map_document_to_checklist_item(document_type: str, category: str, file_name: str) -> dict:
    """
    Map uploaded document to specific checklist items based on document type and file name.
    Returns the target checklist item description or key for matching.
    """
    # Define mapping rules for different document types
    DOCUMENT_MAPPING = {
        # Incorporation Documents
        'incorporation_docs': {
            'keywords': ['certificate of incorporation', 'cac registration', 'memorandum', 'articles', 'form cac7'],
            'target_items': ['Upload Certificate of Incorporation', 'CAC Registration Documents']
        },
        # Tax Documents
        'tax_certificate': {
            'keywords': ['tax clearance', 'firs certificate', 'tax certificate'],
            'target_items': ['Tax Clearance Certificate', 'FIRS Tax Certificate']
        },
        # Financial Statements
        'audited_accounts': {
            'keywords': ['audited accounts', 'financial statement', 'balance sheet', 'profit loss'],
            'target_items': ['Audited Financial Statements', 'Balance Sheet', 'Profit & Loss Statement']
        },
        # Bank Documents
        'bank_statement': {
            'keywords': ['bank statement', 'bank account', 'bank confirmation'],
            'target_items': ['Bank Statements', 'Bank Confirmation Letter']
        },
        # Licenses
        'license': {
            'keywords': ['business license', 'operating license', 'permit'],
            'target_items': ['Business License', 'Operating Permits']
        }
    }
    
    # Default mapping based on document type
    if document_type in DOCUMENT_MAPPING:
        return {
            'document_type': document_type,
            'target_items': DOCUMENT_MAPPING[document_type]['target_items'],
            'keywords': DOCUMENT_MAPPING[document_type]['keywords']
        }
    
    # Fallback: try to match based on file name keywords
    file_name_lower = file_name.lower()
    for doc_type, info in DOCUMENT_MAPPING.items():
        for keyword in info['keywords']:
            if keyword in file_name_lower:
                return {
                    'document_type': doc_type,
                    'target_items': info['target_items'],
                    'keywords': [keyword]
                }
    
    # If no match found, use category-based fallback
    return {
        'document_type': document_type,
        'target_items': [f"Upload {document_type.replace('_', ' ').title()}"],
        'keywords': []
    }

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

        # In your upload_compliance_document function, after successful database insert:
        # Auto-complete checklist items for this category
        auto_complete_checklist_items(user_id, category, document_type, file.filename, supabase)

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
    
# Add this function to your compliance.py backend
def auto_complete_checklist_items(user_id: str, category: str, document_type: str, file_name: str, supabase):
    """Auto-complete SPECIFIC checklist items when documents are uploaded"""
    try:
        # Get the mapping for this document
        mapping = map_document_to_checklist_item(document_type, category, file_name)
        
        # Find checklist items for this user and category that aren't completed
        result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("category", category)\
            .eq("is_completed", False)\
            .execute()
        
        if not result.data:
            return
        
        # Track if we found any matches
        matched_items = []
        
        # Try to match based on target items first
        for item in result.data:
            item_description = item.get('item_description', '').lower()
            
            # Check if this item matches any of our target items
            for target_item in mapping['target_items']:
                if target_item.lower() in item_description:
                    # Mark this SPECIFIC item as complete
                    supabase.from_("audit_checklist_items")\
                        .update({
                            "is_completed": True,
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "completed_by": user_id
                        })\
                        .eq("id", item['id'])\
                        .execute()
                    
                    matched_items.append(item['id'])
                    logger.info(f"✅ Matched and completed checklist item: {item['item_description']}")
                    break
            
            # If no direct match, try keyword matching
            if item['id'] not in matched_items and mapping['keywords']:
                for keyword in mapping['keywords']:
                    if keyword in item_description:
                        # Mark this item as complete
                        supabase.from_("audit_checklist_items")\
                            .update({
                                "is_completed": True,
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                                "completed_by": user_id
                            })\
                            .eq("id", item['id'])\
                            .execute()
                        
                        matched_items.append(item['id'])
                        logger.info(f"✅ Matched by keyword '{keyword}': {item['item_description']}")
                        break
        
        # Log if no matches were found
        if not matched_items:
            logger.warning(f"⚠️ No matching checklist items found for document: {file_name} (type: {document_type})")
        else:
            logger.info(f"✅ Auto-completed {len(matched_items)} checklist items for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to auto-complete checklist: {e}")

@router.delete("/documents/{document_id}")
async def delete_compliance_document(
    document_id: str,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Delete a compliance document from storage and database"""
    try:
        user_id = current_user['id']
        
        # 1. Get the document to find storage_path
        doc_result = supabase.from_("compliance_documents")\
            .select("storage_path, category")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = doc_result.data
        
        # 2. Delete from storage (if storage_path exists)
        if doc.get('storage_path'):
            try:
                supabase.storage.from_("compliance-documents")\
                    .remove([doc['storage_path']])
            except Exception as storage_error:
                logger.warning(f"Failed to delete from storage: {storage_error}")
                # Continue anyway to delete the database record
        
        # 3. Delete from database
        supabase.from_("compliance_documents")\
            .delete()\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        
        logger.info(f"✅ Document deleted: {document_id} by user {user_id}")
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Document Delete] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add this new endpoint to get detailed progress breakdown
@router.get("/checklist/progress-details")
async def get_checklist_progress_details(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Get detailed progress breakdown by category with partial completion support"""
    try:
        user_id = current_user['id']
        
        # Fetch all checklist items
        result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            return {
                "success": True,
                "category_progress": {},
                "overall_progress": 0
            }
        
        # Deduplicate items
        seen_items = {}
        unique_items = []
        
        for item in result.data:
            key = f"{item.get('category', '')}_{item.get('item_description', '')}"
            if key not in seen_items:
                seen_items[key] = True
                unique_items.append(item)
        
        # Group by category and calculate progress
        category_progress = {}
        total_weight = 0
        total_score = 0
        
        # Define category weights (each category contributes equally to overall progress)
        category_weights = {
            'C': 1.0,  # Understanding Business
            'D': 1.0,  # Share Capital
            'E': 1.0,  # Fixed Assets
            'F': 1.0,  # Inventory
            'G': 1.0,  # Debtors
            'H': 1.0,  # Cash & Bank
            'J': 1.0,  # Creditors
            'K': 1.0,  # Sales & Income
            'L': 1.0   # Expenses
        }
        
        for category, weight in category_weights.items():
            category_items = [item for item in unique_items if item.get('category') == category]
            
            if not category_items:
                continue
            
            # Count documents uploaded for this category
            doc_result = supabase.from_("compliance_documents")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("category", category)\
                .execute()
            
            doc_count = len(doc_result.data) if doc_result.data else 0
            
            # Calculate progress for this category
            # Each checklist item contributes equally within the category
            completed_items = sum(1 for item in category_items if item.get('is_completed', False))
            total_items = len(category_items)
            
            # If we have documents but not all items are marked, give partial credit
            # Example: If 2 out of 4 items required and user uploaded 1 document, that's 25% of the category
            if doc_count > 0 and completed_items < total_items:
                # Each document might complete multiple items, but we'll be conservative
                # Give credit proportional to documents uploaded vs expected items
                expected_docs_per_category = total_items  # Usually 1 doc per item
                partial_credit = min(doc_count / expected_docs_per_category, 1.0)
                category_completion = max(completed_items / total_items, partial_credit)
            else:
                category_completion = completed_items / total_items if total_items > 0 else 0
            
            category_progress[category] = {
                'completed_items': completed_items,
                'total_items': total_items,
                'documents_uploaded': doc_count,
                'completion_rate': round(category_completion * 100, 1),
                'weight': weight,
                'contribution': round(category_completion * weight * 100, 1)
            }
            
            total_weight += weight
            total_score += category_completion * weight
        
        # Calculate overall progress
        overall_progress = (total_score / total_weight * 100) if total_weight > 0 else 0
        
        return {
            "success": True,
            "category_progress": category_progress,
            "overall_progress": round(overall_progress, 1)
        }
        
    except Exception as e:
        logger.error(f"[Progress Details] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))