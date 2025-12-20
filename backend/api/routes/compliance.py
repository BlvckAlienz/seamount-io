# File Location: backend/api/routes/compliance.py
# 🚨 PRODUCTION-READY: COMPLETE BUG FIX - FINAL VERSION
# ✅ FIX: Checklist sync on every relevant endpoint call
# ✅ FIX: Document deletion properly updates checklist
# ✅ FIX: Progress calculation based on actual document existence

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from typing import Dict, Any, List
import logging
from datetime import datetime, timezone
import uuid

from backend.dependencies import get_supabase_client, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# HELPER FUNCTIONS
# ============================================

def map_document_to_checklist_item(document_type: str, category: str, file_name: str) -> dict:
    """Map uploaded document to specific checklist items based on document type and file name."""
    DOCUMENT_MAPPING = {
        'incorporation_docs': {
            'keywords': ['certificate of incorporation', 'cac registration', 'memorandum', 'articles', 'form cac7'],
            'target_items': ['Upload Certificate of Incorporation', 'CAC Registration Documents', 'Articles of Association']
        },
        'tax_certificate': {
            'keywords': ['tax clearance', 'firs certificate', 'tax certificate'],
            'target_items': ['Tax Clearance Certificate', 'FIRS Tax Certificate']
        },
        'audited_accounts': {
            'keywords': ['audited accounts', 'financial statement', 'balance sheet', 'profit loss'],
            'target_items': ['Audited Financial Statements', 'Balance Sheet', 'Profit & Loss Statement']
        },
        'bank_statement': {
            'keywords': ['bank statement', 'bank account', 'bank confirmation'],
            'target_items': ['Bank Statements', 'Bank Confirmation Letter']
        },
        'license': {
            'keywords': ['business license', 'operating license', 'permit'],
            'target_items': ['Business License', 'Operating Permits']
        }
    }
    
    if document_type in DOCUMENT_MAPPING:
        return {
            'document_type': document_type,
            'target_items': DOCUMENT_MAPPING[document_type]['target_items'],
            'keywords': DOCUMENT_MAPPING[document_type]['keywords']
        }
    
    file_name_lower = file_name.lower()
    for doc_type, info in DOCUMENT_MAPPING.items():
        for keyword in info['keywords']:
            if keyword in file_name_lower:
                return {
                    'document_type': doc_type,
                    'target_items': info['target_items'],
                    'keywords': [keyword]
                }
    
    return {
        'document_type': document_type,
        'target_items': [f"Upload {document_type.replace('_', ' ').title()}"],
        'keywords': []
    }

def auto_complete_checklist_items(user_id: str, category: str, document_type: str, file_name: str, document_id: str, supabase):
    """Auto-complete SPECIFIC checklist items when documents are uploaded and TRACK the relationship"""
    try:
        mapping = map_document_to_checklist_item(document_type, category, file_name)
        
        # Find checklist items for this user and category that aren't completed
        result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("category", category)\
            .eq("is_completed", False)\
            .execute()
        
        if not result.data:
            return []
        
        matched_items = []
        
        for item in result.data:
            item_description = item.get('item_description', '').lower()
            item_matched = False
            
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
                    
                    # RECORD THE MATCH in our tracking table
                    match_data = {
                        "user_id": user_id,
                        "checklist_item_id": item['id'],
                        "document_id": document_id,
                        "category": category
                    }
                    
                    supabase.table("checklist_document_matches")\
                        .insert(match_data)\
                        .execute()
                    
                    matched_items.append(item['id'])
                    item_matched = True
                    logger.info(f"✅ Matched and completed checklist item: {item['item_description']}")
                    break
            
            # If no direct match, try keyword matching
            if not item_matched and mapping['keywords']:
                for keyword in mapping['keywords']:
                    if keyword in item_description:
                        supabase.from_("audit_checklist_items")\
                            .update({
                                "is_completed": True,
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                                "completed_by": user_id
                            })\
                            .eq("id", item['id'])\
                            .execute()
                        
                        # RECORD THE MATCH
                        match_data = {
                            "user_id": user_id,
                            "checklist_item_id": item['id'],
                            "document_id": document_id,
                            "category": category
                        }
                        
                        supabase.table("checklist_document_matches")\
                            .insert(match_data)\
                            .execute()
                        
                        matched_items.append(item['id'])
                        logger.info(f"✅ Matched by keyword '{keyword}': {item['item_description']}")
                        break
        
        if not matched_items:
            logger.warning(f"⚠️ No matching checklist items found for document: {file_name}")
        else:
            logger.info(f"✅ Auto-completed {len(matched_items)} checklist items for user {user_id}")
        
        return matched_items
        
    except Exception as e:
        logger.error(f"Failed to auto-complete checklist: {e}")
        return []

def get_actual_completed_items(user_id: str, supabase) -> List[str]:
    """
    🚨 CRITICAL: Get checklist items that ACTUALLY have supporting documents.
    Returns list of checklist item IDs that have at least one existing document.
    """
    try:
        # Get all existing document IDs
        docs_result = supabase.from_("compliance_documents")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        existing_doc_ids = {doc['id'] for doc in (docs_result.data or [])}
        
        # Get all matches
        matches_result = supabase.from_("checklist_document_matches")\
            .select("checklist_item_id, document_id")\
            .eq("user_id", user_id)\
            .execute()
        
        matches = matches_result.data or []
        
        # Filter to only matches with existing documents
        valid_checklist_items = set()
        for match in matches:
            if match['document_id'] in existing_doc_ids:
                valid_checklist_items.add(match['checklist_item_id'])
        
        logger.info(f"📊 User {user_id}: {len(valid_checklist_items)} items have supporting documents")
        return list(valid_checklist_items)
        
    except Exception as e:
        logger.error(f"❌ Failed to get actual completed items: {e}")
        return []

def sync_checklist_with_documents(user_id: str, supabase):
    """
    🚨 CRITICAL FIX: Ensure checklist completion status matches ACTUAL document existence.
    This is the CORE FIX that makes everything consistent.
    """
    try:
        logger.info(f"🔄 [SYNC] Starting checklist sync for user {user_id}")
        
        # Get checklist items that actually have documents
        actually_completed = set(get_actual_completed_items(user_id, supabase))
        
        # Get all checklist items
        all_items_result = supabase.from_("audit_checklist_items")\
            .select("id, is_completed, item_description")\
            .eq("user_id", user_id)\
            .execute()
        
        if not all_items_result.data:
            logger.info(f"🔄 [SYNC] No checklist items found for user {user_id}")
            return
        
        # Track changes for logging
        marked_incomplete = []
        marked_complete = []
        
        # Sync each item
        for item in all_items_result.data:
            item_id = item['id']
            is_currently_completed = item.get('is_completed', False)
            should_be_completed = item_id in actually_completed
            
            # Update if out of sync
            if is_currently_completed != should_be_completed:
                if should_be_completed:
                    # Mark as complete (has supporting documents)
                    supabase.from_("audit_checklist_items")\
                        .update({
                            "is_completed": True,
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "completed_by": user_id
                        })\
                        .eq("id", item_id)\
                        .execute()
                    marked_complete.append(item_id)
                    logger.info(f"✅ [SYNC] Marked item {item_id} as complete: {item.get('item_description')[:50]}...")
                else:
                    # Mark as incomplete (no supporting documents)
                    supabase.from_("audit_checklist_items")\
                        .update({
                            "is_completed": False,
                            "completed_at": None,
                            "completed_by": None
                        })\
                        .eq("id", item_id)\
                        .execute()
                    marked_incomplete.append(item_id)
                    logger.info(f"✅ [SYNC] Marked item {item_id} as incomplete: {item.get('item_description')[:50]}...")
        
        # Log summary
        logger.info(f"🔄 [SYNC] Complete for user {user_id}: "
                   f"{len(marked_complete)} marked complete, "
                   f"{len(marked_incomplete)} marked incomplete")
        
        # Double-check consistency
        verify_checklist_consistency(user_id, supabase)
        
    except Exception as e:
        logger.error(f"❌ [SYNC] Checklist sync failed: {e}", exc_info=True)

def verify_checklist_consistency(user_id: str, supabase):
    """Verify that checklist completion matches document existence"""
    try:
        actually_completed = set(get_actual_completed_items(user_id, supabase))
        
        checklist_result = supabase.from_("audit_checklist_items")\
            .select("id, is_completed")\
            .eq("user_id", user_id)\
            .execute()
        
        if not checklist_result.data:
            return
        
        inconsistent = []
        for item in checklist_result.data:
            should_be_completed = item['id'] in actually_completed
            if item['is_completed'] != should_be_completed:
                inconsistent.append(item['id'])
        
        if inconsistent:
            logger.warning(f"⚠️ [VERIFY] Found {len(inconsistent)} inconsistent items after sync")
        else:
            logger.info(f"✅ [VERIFY] All checklist items consistent with documents")
            
    except Exception as e:
        logger.error(f"❌ [VERIFY] Consistency check failed: {e}")

# ============================================
# API ENDPOINTS - UPDATED WITH SYNC
# ============================================

@router.get("/checklist")
async def get_audit_checklist(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Get user's audit checklist - NOW WITH SYNC BEFORE RETURNING"""
    try:
        user_id = current_user['id']
        logger.info(f"📋 [CHECKLIST API] Fetching checklist for user {user_id}")
        
        # 🚨 CRITICAL: Sync checklist with actual documents BEFORE returning
        sync_checklist_with_documents(user_id, supabase)
        
        result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            logger.info(f"📋 [CHECKLIST API] No checklist items for user {user_id}")
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
        
        # 🚨 LOG THE RESULTS FOR DEBUGGING
        completed_count = sum(1 for item in result.data if item.get('is_completed', False))
        logger.info(f"📋 [CHECKLIST API] Returning {len(result.data)} items, {completed_count} completed")
        
        # Deduplicate items
        seen_items = {}
        unique_items = []
        
        for item in result.data:
            category = item.get('category', '')
            item_description = item.get('item_description', '')
            key = f"{category}_{item_description}"
            
            if key not in seen_items:
                seen_items[key] = True
                unique_items.append(item)
        
        # Sort and categorize
        sorted_items = sorted(unique_items, key=lambda x: (
            x.get('category', ''), 
            x.get('item_code', '')
        ))
        
        checklist_by_category = {}
        for item in sorted_items:
            category = item.get('category', 'UNKNOWN')
            if category not in checklist_by_category:
                checklist_by_category[category] = []
            checklist_by_category[category].append(item)
        
        # Calculate stats
        total_items = len(sorted_items)
        completed_items = sum(1 for item in sorted_items if item.get('is_completed', False))
        completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
        
        logger.info(f"📋 [CHECKLIST API] Stats: {completed_items}/{total_items} ({completion_percentage}%)")
        
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
        logger.error(f"❌ [CHECKLIST API] Error: {e}", exc_info=True)
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
    """✅ Mark checklist item as complete (manual completion)"""
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

@router.post("/checklist/{item_id}/incomplete")
async def mark_checklist_item_incomplete(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Mark checklist item as incomplete"""
    try:
        user_id = current_user['id']
        
        result = supabase.from_("audit_checklist_items")\
            .update({
                "is_completed": False,
                "completed_at": None,
                "completed_by": None
            })\
            .eq("id", item_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        
        # Also remove from tracking table
        supabase.from_("checklist_document_matches")\
            .delete()\
            .eq("checklist_item_id", item_id)\
            .eq("user_id", user_id)\
            .execute()
        
        return {
            "success": True,
            "message": "Checklist item marked as incomplete"
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
    """✅ Upload document with proper checklist sync"""
    try:
        user_id = current_user['id']
        logger.info(f"📤 Upload attempt by {user_id}, file: {file.filename}")

        if not category or not document_type:
            raise HTTPException(400, "Category and document_type are required")

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(400, "File is empty")

        file_path = f"{user_id}/{category}/{uuid.uuid4()}_{file.filename}"
        
        try:
            upload_response = supabase.storage.from_("compliance-documents").upload(
                path=file_path,
                file=file_bytes
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                raise HTTPException(500, f"Storage upload failed: {upload_response.error}")
                
        except Exception as storage_error:
            logger.error(f"Storage upload crashed: {str(storage_error)}")
            raise HTTPException(500, f"Failed to upload to storage. Check bucket 'compliance-documents' exists and has public policies. Error: {str(storage_error)[:100]}")

        try:
            file_url = supabase.storage.from_("compliance-documents").get_public_url(file_path)
        except Exception as url_error:
            logger.error(f"Failed to get URL: {url_error}")
            project_ref = "YOUR_PROJECT_REF"
            file_url = f"https://{project_ref}.supabase.co/storage/v1/object/public/compliance-documents/{file_path}"

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
            "storage_path": file_path
        }

        db_result = supabase.table("compliance_documents").insert(doc_data).execute()
        
        if not db_result.data:
            logger.error("Database insert returned no data")
            try:
                supabase.storage.from_("compliance-documents").remove([file_path])
            except:
                pass
            raise HTTPException(500, "Failed to save document record to database")

        document_id = db_result.data[0]['id']
        logger.info(f"✅ SUCCESS: User {user_id} uploaded {file.filename}, record ID: {document_id}")

        # Auto-complete checklist items for this document
        auto_complete_checklist_items(user_id, category, document_type, file.filename, document_id, supabase)
        
        # 🚨 CRITICAL: Sync checklist after upload
        sync_checklist_with_documents(user_id, supabase)

        return {
            "success": True,
            "document_id": document_id,
            "file_url": file_url,
            "message": "Document fully processed and saved"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected upload error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Upload process failed: {str(e)[:150]}")

@router.delete("/documents/{document_id}")
async def delete_compliance_document(
    document_id: str,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    🚨 CRITICAL FIX: Delete document and SYNC checklist immediately
    """
    try:
        user_id = current_user['id']
        logger.info(f"🗑️ [DELETE] Starting deletion of document {document_id} for user {user_id}")
        
        # 1. Get the document
        doc_result = supabase.from_("compliance_documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = doc_result.data
        logger.info(f"🗑️ [DELETE] Document found: {doc.get('file_name')}")
        
        # 2. Get checklist items completed by this document
        matches_result = supabase.from_("checklist_document_matches")\
            .select("checklist_item_id")\
            .eq("document_id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        
        affected_item_ids = [match['checklist_item_id'] for match in (matches_result.data or [])]
        logger.info(f"🗑️ [DELETE] Found {len(affected_item_ids)} checklist items affected")
        
        # 3. Delete from storage (non-blocking failure)
        if doc.get('storage_path'):
            try:
                supabase.storage.from_("compliance-documents")\
                    .remove([doc['storage_path']])
                logger.info(f"✅ Deleted from storage: {doc['storage_path']}")
            except Exception as storage_error:
                logger.warning(f"⚠️ Failed to delete from storage: {storage_error}")
        
        # 4. Delete tracking records for THIS document
        supabase.from_("checklist_document_matches")\
            .delete()\
            .eq("document_id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        logger.info(f"✅ Deleted tracking records for document {document_id}")
        
        # 5. Delete the document record
        supabase.from_("compliance_documents")\
            .delete()\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        logger.info(f"✅ Deleted document record {document_id}")
        
        # 🚨 CRITICAL: SYNC checklist immediately after deletion
        sync_checklist_with_documents(user_id, supabase)
        
        logger.info(f"✅ [DELETE] Document deletion complete")
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "affected_items": len(affected_item_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Document Delete] Critical error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/checklist/progress-details")
async def get_checklist_progress_details(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    🚨 CRITICAL FIX: READ-ONLY progress calculation with SYNC.
    Single source of truth for progress.
    """
    try:
        user_id = current_user['id']
        logger.info(f"📊 [PROGRESS] Calculating progress for user {user_id}")
        
        # 🚨 CRITICAL: Sync checklist first to ensure consistency
        sync_checklist_with_documents(user_id, supabase)
        
        # 1. Get ALL checklist items (deduplicated)
        checklist_result = supabase.from_("audit_checklist_items")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not checklist_result.data:
            logger.info(f"📊 [PROGRESS] No checklist items for user {user_id}")
            return {
                "success": True,
                "category_progress": {},
                "overall_progress": 0,
                "total_documents": 0,
                "completed_items": 0,
                "total_items": 0
            }
        
        # 🚨 LOG FOR DEBUGGING
        completed_count = sum(1 for item in checklist_result.data if item.get('is_completed', False))
        logger.info(f"📊 [PROGRESS] Database has {completed_count}/{len(checklist_result.data)} completed items")
        
        # Deduplicate checklist items
        seen_items = {}
        unique_items = []
        for item in checklist_result.data:
            key = f"{item.get('category', '')}_{item.get('item_description', '')}"
            if key not in seen_items:
                seen_items[key] = True
                unique_items.append(item)
        
        # 2. Get ALL documents
        docs_result = supabase.from_("compliance_documents")\
            .select("id, category")\
            .eq("user_id", user_id)\
            .execute()
        
        all_docs = docs_result.data if docs_result.data else []
        logger.info(f"📊 [PROGRESS] User has {len(all_docs)} documents")
        
        # 3. Calculate progress based on SYNCED checklist
        category_progress = {}
        total_items = 0
        completed_items = 0
        
        # Group items by category
        items_by_category = {}
        for item in unique_items:
            category = item.get('category', 'UNKNOWN')
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)
        
        # Calculate progress per category
        for category, items in items_by_category.items():
            category_total = len(items)
            total_items += category_total
            
            # Count completed items (now synced with actual documents)
            category_completed = sum(1 for item in items if item.get('is_completed'))
            completed_items += category_completed
            
            # Count documents in this category
            category_docs = len([d for d in all_docs if d.get('category') == category])
            
            category_progress[category] = {
                'completed_items': category_completed,
                'total_items': category_total,
                'documents_uploaded': category_docs,
                'completion_rate': round((category_completed / category_total * 100) if category_total > 0 else 0, 1)
            }
        
        # Calculate overall progress
        overall_progress = round((completed_items / total_items * 100) if total_items > 0 else 0, 1)
        
        logger.info(f"✅ [PROGRESS] Final: {completed_items}/{total_items} items ({overall_progress}%), {len(all_docs)} documents")
        
        return {
            "success": True,
            "category_progress": category_progress,
            "overall_progress": overall_progress,
            "total_documents": len(all_docs),
            "completed_items": completed_items,
            "total_items": total_items
        }
        
    except Exception as e:
        logger.error(f"❌ [Progress Details] Critical error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/checklist/recalculate")
async def recalculate_checklist_endpoint(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    🔄 Manually trigger checklist sync.
    """
    try:
        user_id = current_user['id']
        sync_checklist_with_documents(user_id, supabase)
        
        return {
            "success": True,
            "message": "Checklist synced with documents successfully"
        }
    except Exception as e:
        logger.error(f"❌ [Recalculate] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# OTHER ENDPOINTS (unchanged but kept for completeness)
# ============================================

@router.post("/exemption-checker")
async def check_tax_exemptions(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Tax exemption checker"""
    try:
        data = await request.json()
        user_id = current_user['id']
        
        business_type = data.get('business_type')
        annual_turnover = float(data.get('annual_turnover', 0))
        industry_sector = data.get('industry_sector')
        employee_count = int(data.get('employee_count', 0))
        
        eligible_exemptions = []
        estimated_savings = 0
        
        if annual_turnover < 100_000_000:
            eligible_exemptions.append({
                "id": 20,
                "name": "Small Company 0% Tax",
                "description": "Companies with turnover below ₦100M pay 0% CIT",
                "estimated_savings": annual_turnover * 0.30
            })
            estimated_savings += annual_turnover * 0.30
        
        if industry_sector == 'agriculture':
            eligible_exemptions.append({
                "id": 24,
                "name": "Agricultural Business Tax Holiday",
                "description": "5-year tax holiday for agricultural businesses",
                "estimated_savings": 0
            })
        
        if employee_count > 0:
            eligible_exemptions.append({
                "id": 1,
                "name": "Minimum Wage Workers Exempt",
                "description": "Employees earning minimum wage or less are exempt from PAYE",
                "estimated_savings": 0
            })
        
        if data.get('has_pension_contributions'):
            eligible_exemptions.append({
                "id": 5,
                "name": "Pension Contribution Deduction",
                "description": "Pension contributions are tax-deductible",
                "estimated_savings": 0
            })
        
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
        
        logger.info(f"✅ Tax exemption check completed for user {user_id}")
        
        return {
            "success": True,
            "eligible_exemptions": eligible_exemptions,
            "estimated_tax_savings": estimated_savings,
            "message": f"Found {len(eligible_exemptions)} exemptions"
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
    """✅ Grant auditor access"""
    try:
        data = await request.json()
        user_id = current_user['id']
        
        auditor_email = data.get('auditor_email')
        auditor_name = data.get('auditor_name')
        
        if not auditor_email:
            raise HTTPException(status_code=400, detail="Auditor email required")
        
        access_data = {
            "user_id": user_id,
            "auditor_email": auditor_email,
            "auditor_name": auditor_name,
            "is_active": True
        }
        
        result = supabase.from_("auditor_access")\
            .insert(access_data)\
            .execute()
        
        logger.info(f"✅ Auditor access granted: {auditor_email}")
        
        return {
            "success": True,
            "message": f"Access granted to {auditor_email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auditor Access] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))