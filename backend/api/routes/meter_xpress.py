# File: backend/api/routes/meter_xpress.py
"""
🔌 METER XPRESS API - Seamount's Meter Application Portal
Handles meter application workflow from classification to payment
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import logging

from backend.dependencies import get_current_user, get_db_service
from backend.services.payment_providers.paystack import PaystackProvider
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meter-xpress", tags=["Meter Xpress"])

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class QuestionnaireRequest(BaseModel):
    has_existing_account: bool
    has_working_meter: Optional[bool] = None
    desired_action: Optional[str] = None  # 'convert', 'upgrade', 'downgrade'

class ApplicationInitRequest(BaseModel):
    application_type: str  # 'new_service', 'replacement', 'conversion'
    questionnaire_answers: Dict[str, Any]

class NewServiceFormRequest(BaseModel):
    # Customer Data
    supply_type: str  # 'Prepaid', 'Postpaid KCG', 'Postpaid Non-KCG'
    first_name: str
    middle_name: Optional[str] = None
    surname: str
    customer_type: str
    personal_id_type: str
    date_of_birth: str
    ownership_status: str  # 'Landlord', 'Tenant'
    nationality: str
    gender: str
    primary_email: EmailStr
    mobile_number: str
    phone_2: Optional[str] = None
    
    # Service Point Data
    state: str = "Lagos"
    district: str
    city: Optional[str] = None
    premise_type: str
    premise_category: str
    activity: str
    sub_activity: Optional[str] = None
    state_of_building: str
    applicant_capacity: str
    landmark: str
    pole_number: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Metering
    phase: str  # '1 Phase', '3 Phase'
    voltage_level: str  # '230V', '400V'
    map_vendor: str
    
    # Electrical Appliances (optional)
    appliances: Optional[List[Dict[str, Any]]] = []

class ReplacementFormRequest(BaseModel):
    meter_number: str  # ✅ CHANGE from account_number to meter_number
    state_of_building: str
    applicant_capacity: str
    map_vendor: str
    phase: str
    voltage_level: str

class ConversionFormRequest(BaseModel):
    account_number: Optional[str] = None
    meter_number: Optional[str] = None
    conversion_from: str  # 'postpaid_metered', 'prepaid_metered', 'unmetered'
    conversion_to: str    # 'prepaid_metered', 'postpaid_metered', 'unmetered'
    map_vendor: Optional[str] = None  # Required if converting TO metered
    phase: Optional[str] = None
    voltage_level: Optional[str] = None

# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_service_fee(base_price: Decimal, phase_type: str) -> Dict[str, Decimal]:
    """Calculate service fees with 60%/50% markup"""
    markup_rate = Decimal("0.60") if phase_type == "1phase" else Decimal("0.50")
    
    service_fee = base_price * markup_rate
    total_amount = base_price + service_fee
    
    return {
        "base_price": base_price,
        "service_fee": service_fee,
        "total_amount": total_amount,
        "markup_percentage": markup_rate * 100
    }

# ============================================
# ENDPOINTS
# ============================================

@router.post("/classify")
async def classify_application(
    request: QuestionnaireRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🎯 STEP 1: Classify meter application type based on questionnaire
    """
    try:
        user_id = current_user['id']
        
        # Classification logic
        if not request.has_existing_account:
            application_type = "new_service"
            message = "New Service Connection - You're applying for the first time"
        elif request.has_working_meter is False:
            application_type = "replacement"
            message = "Meter Replacement - Your previous meter is faulty"
        elif request.has_working_meter is True:
            if request.desired_action == "convert":
                application_type = "conversion"
                message = "Meter Conversion - Changing your meter type"
            elif request.desired_action in ["upgrade", "downgrade"]:
                application_type = request.desired_action
                message = f"Meter {request.desired_action.title()} - Contact support@seamount.io"
            else:
                raise HTTPException(400, "Invalid desired action")
        else:
            raise HTTPException(400, "Invalid questionnaire responses")
        
        logger.info(f"📋 Classified application for user {user_id}: {application_type}")
        
        return {
            "success": True,
            "application_type": application_type,
            "message": message,
            "next_step": "form_details" if application_type in ["new_service", "replacement", "conversion"] else "contact_support"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Classification failed: {e}")
        raise HTTPException(500, f"Classification failed: {str(e)}")


@router.post("/applications/new-service")
async def create_new_service_application(
    form_data: NewServiceFormRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📝 STEP 2: Create new service application
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # Get MAP pricing
        phase_type = "1phase" if form_data.phase == "1 Phase" else "3phase"
        
        map_result = supabase.from_("map_pricing")\
            .select("*")\
            .eq("vendor_name", form_data.map_vendor)\
            .eq("is_active", True)\
            .single()\
            .execute()
        
        if not map_result.data:
            raise HTTPException(404, f"MAP vendor '{form_data.map_vendor}' not found")
        
        base_price = Decimal(str(
            map_result.data['single_phase_price'] if phase_type == "1phase" 
            else map_result.data['three_phase_price']
        ))
        
        # Calculate fees
        pricing = calculate_service_fee(base_price, phase_type)
        
        # Create application
        app_data = {
            "user_id": user_id,
            "application_type": "new_service",
            "status": "draft",
            "form_data": form_data.dict(),
            "supply_type": form_data.supply_type,
            "phase_type": phase_type,
            "voltage_level": form_data.voltage_level,
            "map_vendor": form_data.map_vendor,
            "map_base_price": float(pricing['base_price']),
            "service_fee": float(pricing['service_fee']),
            "total_amount": float(pricing['total_amount']),
            "district": form_data.district,
            "address": form_data.landmark,
            "metadata": {
                "customer_type": form_data.customer_type,
                "premise_type": form_data.premise_type
            }
        }
        
        result = supabase.from_("meter_applications").insert(app_data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create application")
        
        application_id = result.data[0]['id']
        
        logger.info(f"✅ New service application created: {application_id}")
        
        return {
            "success": True,
            "application_id": application_id,
            "pricing": {
                "base_price": float(pricing['base_price']),
                "service_fee": float(pricing['service_fee']),
                "total_amount": float(pricing['total_amount']),
                "markup_percentage": float(pricing['markup_percentage'])
            },
            "next_step": "document_upload"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ New service application failed: {e}")
        raise HTTPException(500, str(e))

@router.post("/applications/replacement")
async def create_replacement_application(
    form_data: ReplacementFormRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📝 Create meter replacement application
    """
    try:
        # ✅ FIXED DEBUG LOG:
        logger.info(f"📦 Received replacement form data: {form_data.dict()}")
        logger.info(f"🔍 Meter number from request: {form_data.meter_number}")  # ✅ THIS IS NOW CORRECT
        
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # Get MAP pricing
        phase_type = "1phase" if form_data.phase == "1 Phase" else "3phase"
        
        map_result = supabase.from_("map_pricing")\
            .select("*")\
            .eq("vendor_name", form_data.map_vendor)\
            .eq("is_active", True)\
            .single()\
            .execute()
        
        if not map_result.data:
            raise HTTPException(404, f"MAP vendor '{form_data.map_vendor}' not found")
        
        base_price = Decimal(str(
            map_result.data['single_phase_price'] if phase_type == "1phase" 
            else map_result.data['three_phase_price']
        ))
        
        # Calculate fees
        pricing = calculate_service_fee(base_price, phase_type)
        
        # Create application
        app_data = {
            "user_id": user_id,
            "application_type": "replacement",
            "status": "draft",
            "form_data": form_data.dict(),
            "phase_type": phase_type,
            "voltage_level": form_data.voltage_level,
            "map_vendor": form_data.map_vendor,
            "map_base_price": float(pricing['base_price']),
            "service_fee": float(pricing['service_fee']),
            "total_amount": float(pricing['total_amount']),
            # ✅ FIX: Changed from account_number to meter_number
            "metadata": {
                "meter_number": form_data.meter_number,  # THIS IS THE FIX
                "state_of_building": form_data.state_of_building,
                "applicant_capacity": form_data.applicant_capacity
            }
        }
        
        result = supabase.from_("meter_applications").insert(app_data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create application")
        
        application_id = result.data[0]['id']
        
        logger.info(f"✅ Replacement application created: {application_id}")
        
        return {
            "success": True,
            "application_id": application_id,
            "pricing": {
                "base_price": float(pricing['base_price']),
                "service_fee": float(pricing['service_fee']),
                "total_amount": float(pricing['total_amount']),
                "markup_percentage": float(pricing['markup_percentage'])
            },
            "next_step": "document_upload"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Replacement application failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/applications/conversion")
async def create_conversion_application(
    form_data: ConversionFormRequest,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🔄 Create meter conversion application
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # Determine if new meter is needed
        needs_meter = any([
            'prepaid_metered' in form_data.conversion_to.lower(),
            'postpaid_metered' in form_data.conversion_to.lower()
        ])
        
        pricing = None
        if needs_meter:
            if not form_data.map_vendor:
                raise HTTPException(400, "MAP vendor required for metered conversion")
            
            # Get MAP pricing
            phase_type = "1phase" if form_data.phase == "1 Phase" else "3phase"
            
            map_result = supabase.from_("map_pricing")\
                .select("*")\
                .eq("vendor_name", form_data.map_vendor)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if not map_result.data:
                raise HTTPException(404, f"MAP vendor '{form_data.map_vendor}' not found")
            
            base_price = Decimal(str(
                map_result.data['single_phase_price'] if phase_type == "1phase" 
                else map_result.data['three_phase_price']
            ))
            
            pricing = calculate_service_fee(base_price, phase_type)
        
        # Create application
        app_data = {
            "user_id": user_id,
            "application_type": "conversion",
            "status": "draft",
            "form_data": form_data.dict(),
            "phase_type": "1phase" if form_data.phase == "1 Phase" else "3phase" if needs_meter else None,
            "voltage_level": form_data.voltage_level if needs_meter else None,
            "map_vendor": form_data.map_vendor if needs_meter else None,
            "map_base_price": float(pricing['base_price']) if pricing else 0,
            "service_fee": float(pricing['service_fee']) if pricing else 0,
            "total_amount": float(pricing['total_amount']) if pricing else 0,
            "metadata": {
                "account_number": form_data.account_number,
                "meter_number": form_data.meter_number,
                "conversion_from": form_data.conversion_from,
                "conversion_to": form_data.conversion_to,
                "needs_meter": needs_meter
            }
        }
        
        result = supabase.from_("meter_applications").insert(app_data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create application")
        
        application_id = result.data[0]['id']
        
        logger.info(f"✅ Conversion application created: {application_id}")
        
        return {
            "success": True,
            "application_id": application_id,
            "needs_meter": needs_meter,
            "pricing": {
                "base_price": float(pricing['base_price']),
                "service_fee": float(pricing['service_fee']),
                "total_amount": float(pricing['total_amount']),
                "markup_percentage": float(pricing['markup_percentage'])
            } if pricing else None,
            "next_step": "document_upload" if needs_meter else "submission"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Conversion application failed: {e}")
        raise HTTPException(500, str(e))

@router.delete("/applications/{application_id}/documents/{document_id}")
async def delete_application_document(
    application_id: str,
    document_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🗑️ STEP 3A: Delete uploaded document from storage and database
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # 1. Verify document belongs to user and application
        doc_result = supabase.from_("meter_documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("application_id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(404, "Document not found or access denied")
        
        document = doc_result.data
        
        # 2. Verify application is still in draft state
        app_result = supabase.from_("meter_applications")\
            .select("status")\
            .eq("id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not app_result.data:
            raise HTTPException(404, "Application not found")
        
        if app_result.data['status'] not in ['draft', 'pending_payment']:
            raise HTTPException(400, "Cannot delete documents from submitted application")
        
        # 3. Delete from Supabase Storage
        if document.get('storage_path'):
            try:
                supabase.storage.from_("meter-documents").remove([document['storage_path']])
                logger.info(f"🗑️ Storage deleted: {document['storage_path']}")
            except Exception as storage_error:
                logger.warning(f"⚠️ Storage deletion warning: {storage_error}")
                # Continue with DB deletion even if storage fails
        
        # 4. Delete from database
        delete_result = supabase.from_("meter_documents")\
            .delete()\
            .eq("id", document_id)\
            .execute()
        
        if not delete_result.data:
            raise HTTPException(500, "Failed to delete document record")
        
        logger.info(f"✅ Document deleted: {document['file_name']} from app {application_id}")
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "deleted_document": {
                "id": document_id,
                "file_name": document['file_name']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document deletion failed: {e}")
        raise HTTPException(500, str(e))
       
@router.post("/applications/{application_id}/documents/upload")
async def upload_application_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📤 STEP 3: Upload required documents
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # Verify application ownership
        app_result = supabase.from_("meter_applications")\
            .select("id, status")\
            .eq("id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not app_result.data:
            raise HTTPException(404, "Application not found")
        
        if app_result.data['status'] not in ['draft', 'pending_payment']:
            raise HTTPException(400, "Cannot upload documents to submitted application")
        
        # Validate file
        if file.size > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(400, "File size exceeds 5MB limit")
        
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise HTTPException(400, "Invalid file type. Only PDF, JPG, PNG allowed")
        
        # Upload to storage
        file_bytes = await file.read()
        file_path = f"meter-xpress/{user_id}/{application_id}/{uuid.uuid4()}_{file.filename}"
        
        upload_response = supabase.storage.from_("meter-documents").upload(
            path=file_path,
            file=file_bytes
        )
        
        if hasattr(upload_response, 'error') and upload_response.error:
            raise HTTPException(500, f"Storage upload failed: {upload_response.error}")
        
        # Get public URL
        file_url = supabase.storage.from_("meter-documents").get_public_url(file_path)
        
        # Save document record
        doc_data = {
            "application_id": application_id,
            "user_id": user_id,
            "document_type": document_type,
            "file_name": file.filename,
            "file_url": file_url,
            "storage_path": file_path,
            "file_size": file.size,
            "mime_type": file.content_type
        }
        
        doc_result = supabase.from_("meter_documents").insert(doc_data).execute()
        
        if not doc_result.data:
            raise HTTPException(500, "Failed to save document record")
        
        logger.info(f"✅ Document uploaded: {file.filename} for application {application_id}")
        
        return {
            "success": True,
            "document_id": doc_result.data[0]['id'],
            "file_url": file_url,
            "message": "Document uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document upload failed: {e}")
        raise HTTPException(500, str(e))

@router.delete("/applications/{application_id}/cancel")
async def cancel_draft_application(
    application_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🚫 Cancel a draft application and clean up associated documents
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # 1. Get application
        app_result = supabase.from_("meter_applications")\
            .select("id, status")\
            .eq("id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not app_result.data:
            raise HTTPException(404, "Application not found")
        
        if app_result.data['status'] not in ['draft', 'pending_payment']:
            raise HTTPException(400, "Only draft applications can be cancelled")
        
        # 2. Get all documents for this application
        docs_result = supabase.from_("meter_documents")\
            .select("id, storage_path")\
            .eq("application_id", application_id)\
            .execute()
        
        # 3. Delete documents from storage
        if docs_result.data:
            storage_paths = [doc['storage_path'] for doc in docs_result.data if doc.get('storage_path')]
            if storage_paths:
                try:
                    supabase.storage.from_("meter-documents").remove(storage_paths)
                    logger.info(f"🗑️ Deleted {len(storage_paths)} files from storage")
                except Exception as storage_error:
                    logger.warning(f"⚠️ Storage cleanup warning: {storage_error}")
        
        # 4. Delete document records
        supabase.from_("meter_documents")\
            .delete()\
            .eq("application_id", application_id)\
            .execute()
        
        # 5. Delete application record
        delete_result = supabase.from_("meter_applications")\
            .delete()\
            .eq("id", application_id)\
            .execute()
        
        logger.info(f"✅ Draft application cancelled: {application_id}")
        
        return {
            "success": True,
            "message": "Draft application cancelled and cleaned up",
            "cancelled_application": application_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Application cancellation failed: {e}")
        raise HTTPException(500, str(e))
    
@router.get("/applications/{application_id}")
async def get_application_details(
    application_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📋 Get application details with documents
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # Get application
        app_result = supabase.from_("meter_applications")\
            .select("*")\
            .eq("id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not app_result.data:
            raise HTTPException(404, "Application not found")
        
        # Get documents
        docs_result = supabase.from_("meter_documents")\
            .select("*")\
            .eq("application_id", application_id)\
            .execute()
        
        return {
            "success": True,
            "application": app_result.data,
            "documents": docs_result.data or []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch application: {e}")
        raise HTTPException(500, str(e))


@router.post("/applications/{application_id}/submit")
async def submit_application_for_payment(
    application_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    💳 STEP 4: Submit application and initialize payment
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        settings = get_settings()
        
        # Get application
        app_result = supabase.from_("meter_applications")\
            .select("*")\
            .eq("id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not app_result.data:
            raise HTTPException(404, "Application not found")
        
        app = app_result.data
        
        if app['status'] != 'draft':
            raise HTTPException(400, "Application already submitted")
        
        # Validate documents
        docs_result = supabase.from_("meter_documents")\
            .select("document_type")\
            .eq("application_id", application_id)\
            .execute()
        
        # ✅ NEW CODE (no lecan_cert):
        if app['application_type'] == 'new_service':
            required_docs = ['passport_photo', 'id_card']
        elif app['application_type'] == 'replacement':
            required_docs = ['id_card', 'meter_photo']
        elif app['application_type'] == 'conversion':
            # Only require ID if converting TO metered
            if app.get('metadata', {}).get('needs_meter', False):
                required_docs = ['id_card']
            else:
                required_docs = []
        uploaded_types = [doc['document_type'] for doc in (docs_result.data or [])]
        
        missing_docs = [doc for doc in required_docs if doc not in uploaded_types]
        if missing_docs:
            raise HTTPException(400, f"Missing required documents: {', '.join(missing_docs)}")
        
        # Initialize Paystack payment
        paystack = PaystackProvider(settings)
        payment_ref = f"METER_{application_id[:8]}_{int(datetime.now().timestamp())}"
        
        payment_result = await paystack.initialize_payment(
            amount=float(app['total_amount']),
            currency="NGN",
            email=current_user['email'],
            tx_ref=payment_ref,
            name=current_user.get('first_name', 'User')
        )
        
        if not payment_result or payment_result.get('status') != 'success':
            raise HTTPException(500, "Payment initialization failed")
        
        payment_link = payment_result.get('authorization_url') or payment_result.get('payment_link')
        
        if not payment_link:
            raise HTTPException(500, "No payment link returned")
        
        # Update application
        supabase.from_("meter_applications")\
            .update({
                "status": "pending_payment",
                "payment_reference": payment_ref,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })\
            .eq("id", application_id)\
            .execute()
        
        logger.info(f"✅ Application {application_id} submitted for payment")
        
        return {
            "success": True,
            "payment_link": payment_link,
            "payment_reference": payment_ref,
            "amount": app['total_amount'],
            "message": "Application ready for payment"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Application submission failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/map-pricing")
async def get_map_pricing(
    phase: Optional[str] = None,
    db_service = Depends(get_db_service)
):
    """
    💰 Get MAP vendor pricing with service fees
    """
    try:
        supabase = db_service.supabase
        
        result = supabase.from_("map_pricing")\
            .select("*")\
            .eq("is_active", True)\
            .order("single_phase_price")\
            .execute()
        
        if not result.data:
            return {"success": True, "pricing": []}
        
        pricing_data = []
        for vendor in result.data:
            if not phase or phase == "1phase":
                base_price = Decimal(str(vendor['single_phase_price']))
                fees = calculate_service_fee(base_price, "1phase")
                pricing_data.append({
                    "vendor_name": vendor['vendor_name'],
                    "phase": "1phase",
                    "base_price": float(base_price),
                    "service_fee": float(fees['service_fee']),
                    "total_price": float(fees['total_amount']),
                    "markup_percentage": float(fees['markup_percentage'])
                })
            
            if not phase or phase == "3phase":
                base_price = Decimal(str(vendor['three_phase_price']))
                fees = calculate_service_fee(base_price, "3phase")
                pricing_data.append({
                    "vendor_name": vendor['vendor_name'],
                    "phase": "3phase",
                    "base_price": float(base_price),
                    "service_fee": float(fees['service_fee']),
                    "total_price": float(fees['total_amount']),
                    "markup_percentage": float(fees['markup_percentage'])
                })
        
        # Sort by total price
        pricing_data.sort(key=lambda x: x['total_price'])
        
        return {
            "success": True,
            "pricing": pricing_data
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch MAP pricing: {e}")
        raise HTTPException(500, str(e))


@router.get("/lecan-contractors")
async def search_lecan_contractors(
    district: Optional[str] = None,
    location: Optional[str] = None,
    db_service = Depends(get_db_service)
):
    """
    🔍 Search LECAN contractors by location
    """
    try:
        supabase = db_service.supabase
        
        query = supabase.from_("lecan_contractors")\
            .select("*")\
            .eq("is_active", True)
        
        if district:
            query = query.ilike("district", f"%{district}%")
        
        if location:
            query = query.ilike("location", f"%{location}%")
        
        result = query.order("experience_years", desc=True).execute()
        
        return {
            "success": True,
            "contractors": result.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ LECAN search failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/my-applications")
async def get_user_applications(
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    📱 Get user's meter applications
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        result = supabase.from_("meter_applications")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {
            "success": True,
            "applications": result.data or []
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch user applications: {e}")
        raise HTTPException(500, str(e))
    
@router.post("/webhook/paystack")
async def handle_paystack_webhook(
    request: Request,
    db_service = Depends(get_db_service)
):
    """
    🔔 Handle Paystack payment confirmation webhook
    """
    try:
        payload = await request.json()
        logger.info(f"🔔 Paystack webhook received: {payload.get('event')}")
        
        # Verify signature (IMPORTANT FOR PRODUCTION)
        settings = get_settings()
        signature = request.headers.get("x-paystack-signature")
        
        # TODO: Verify signature with Paystack webhook secret
        
        if payload.get('event') == 'charge.success':
            reference = payload['data']['reference']
            
            # Update application status
            supabase = db_service.supabase
            
            result = supabase.from_("meter_applications")\
                .update({
                    "status": "submitted",
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })\
                .eq("payment_reference", reference)\
                .execute()
            
            if result.data:
                app = result.data[0]
                
                # Send confirmation email
                try:
                    from backend.services.email_service import EmailService
                    email_service = EmailService()
                    
                    form_data = app.get('form_data', {})
                    
                    await email_service.send_meter_application_confirmation(
                        to_email=form_data.get('primary_email'),
                        customer_name=f"{form_data.get('first_name')} {form_data.get('surname')}",
                        application_id=app['id'],
                        application_type=app['application_type'],
                        map_vendor=app['map_vendor'],
                        phase_type=app['phase_type'],
                        district=app.get('district', 'N/A'),
                        total_amount=app['total_amount']
                    )
                except Exception as email_error:
                    logger.error(f"Failed to send confirmation email: {email_error}")
                
                logger.info(f"✅ Application {app['id']} marked as submitted")
            
        return {"status": "success", "processed": True}
        
    except Exception as e:
        logger.error(f"❌ Webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}
    
@router.delete("/applications/{application_id}/documents/{document_id}")
async def delete_application_document(
    application_id: str,
    document_id: str,
    current_user: Dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """
    🗑️ Delete an uploaded document (from both database and storage)
    """
    try:
        user_id = current_user['id']
        supabase = db_service.supabase
        
        # First, get the document to retrieve storage path
        doc_result = supabase.from_("meter_documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("application_id", application_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(404, "Document not found")
        
        document = doc_result.data
        
        # Delete from Supabase storage first
        if document.get('storage_path'):
            try:
                supabase.storage.from_("meter-documents").remove([document['storage_path']])
            except Exception as storage_error:
                logger.warning(f"Storage deletion failed (file might not exist): {storage_error}")
        
        # Then delete the database record
        delete_result = supabase.from_("meter_documents")\
            .delete()\
            .eq("id", document_id)\
            .execute()
        
        logger.info(f"✅ Document deleted: {document['file_name']} for application {application_id}")
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document deletion failed: {e}")
        raise HTTPException(500, str(e))