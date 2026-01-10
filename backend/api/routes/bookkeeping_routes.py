# backend/api/routes/bookkeeping_routes.py
"""
Bookkeeping API Routes - Bank Statement Processing & Trial Balance Generation
"""

import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
from decimal import Decimal
import io
import os
import tempfile

from backend.dependencies import (
    get_supabase_client,
    get_current_user,
    get_db_service
)
from supabase import Client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/bookkeeping", tags=["Bookkeeping"])

# =====================================================
# PYDANTIC MODELS
# =====================================================

class BankStatementUploadResponse(BaseModel):
    success: bool
    statement_id: Optional[str] = None
    file_name: str
    transaction_count: int
    parsing_status: str
    message: str
    metadata: Optional[Dict] = None

class TransactionCategorizationRequest(BaseModel):
    statement_id: str
    use_ai: bool = True

class TransactionUpdateRequest(BaseModel):
    transaction_id: str
    account_code: str
    category: str
    notes: Optional[str] = None

class TrialBalanceRequest(BaseModel):
    period_start: date = Field(..., description="Start date (YYYY-MM-DD)")
    period_end: date = Field(..., description="End date (YYYY-MM-DD)")
    save_report: bool = True

class TrialBalanceExportRequest(BaseModel):
    report_id: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    company_name: str = "Your Company"

# =====================================================
# 1️⃣ BANK STATEMENT UPLOAD & PARSING
# =====================================================

@router.post("/upload-statement", response_model=BankStatementUploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📤 Upload and parse bank statement (CSV, Excel, PDF)
    """
    try:
        logger.info(f"🔵 UPLOAD START: User {current_user['id']}, File: {file.filename}")
        
        user_id = current_user['id']
        
        # 1️⃣ VALIDATE FILE
        allowed_extensions = ['csv', 'xlsx', 'xls', 'pdf']
        file_ext = file.filename.split('.')[-1].lower()
        
        logger.info(f"🔵 File extension: {file_ext}")
        
        if file_ext not in allowed_extensions:
            logger.error(f"❌ Invalid file type: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (max 10MB)
        temp_content = await file.read()
        file_size = len(temp_content)
        
        logger.info(f"🔵 File size: {file_size} bytes ({file_size / 1024:.2f} KB)")
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            logger.error(f"❌ File too large: {file_size} bytes")
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 10MB limit"
            )
        
        # Reset file pointer for temp file creation
        await file.seek(0)
        
        # 2️⃣ SAVE TO TEMP FILE
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"🔵 Saved to temp file: {tmp_file_path}")
        
        try:
            # 3️⃣ PARSE BANK STATEMENT
            from backend.services.bookkeeping.parser_service import BankStatementParser
            
            logger.info("🔵 Initializing parser...")
            parser = BankStatementParser()
            
            logger.info(f"🔵 Parsing file: {tmp_file_path} (type: {file_ext})")
            
            # Try to parse
            parse_result = parser.parse_file(tmp_file_path, file_ext)
            
            logger.info(f"🔵 Parse result success: {parse_result.get('success')}")
            
            if not parse_result.get('success'):
                error_msg = parse_result.get('error', 'Unknown error')
                logger.error(f"❌ Parsing failed: {error_msg}")
                
                # For PDFs, try to extract more debugging info
                if file_ext == 'pdf':
                    try:
                        # Extract raw text for debugging
                        raw_text = parser._extract_pdf_text(tmp_file_path)
                        logger.info(f"🔵 Raw text length: {len(raw_text)}")
                        
                        # Try to find transaction lines manually
                        lines = raw_text.split('\n')
                        logger.info("🔵 Looking for transaction patterns...")
                        
                        found_patterns = []
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if len(line) > 20 and any(x in line for x in ['Jan-24', 'Feb-24', 'Mar-24', 'Apr-24', 'May-24']):
                                found_patterns.append(f"Line {i}: {line[:100]}...")
                                if len(found_patterns) <= 3:
                                    logger.info(f"  Found pattern: {line[:100]}...")
                        
                        if found_patterns:
                            logger.info(f"🔵 Found {len(found_patterns)} potential transaction lines")
                        
                        # Try alternative parsing
                        logger.info("🔵 Trying alternative parsing method...")
                        metadata = parser._extract_metadata_from_pdf_text(raw_text)
                        transactions = parser._extract_transactions_from_pdf_text_enhanced(raw_text)
                        
                        if transactions:
                            logger.info(f"🔵 Alternative parsing found {len(transactions)} transactions!")
                            parse_result = {
                                'success': True,
                                'transactions': transactions,
                                'metadata': metadata
                            }
                        else:
                            logger.error("🔵 No transactions found with alternative parsing")
                            
                    except Exception as debug_error:
                        logger.error(f"🔵 Debug extraction failed: {debug_error}")
                
                # If still not successful, raise error
                if not parse_result.get('success'):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parsing failed: {error_msg}"
                    )
            
            transactions = parse_result.get('transactions', [])
            metadata = parse_result.get('metadata', {})
            
            logger.info(f"✅ Parsed {len(transactions)} transactions")
            
            if transactions:
                logger.info(f"🔵 Sample transaction: {transactions[0]}")
            
            logger.info(f"🔵 Metadata: {metadata}")
            
            # 4️⃣ SAVE STATEMENT METADATA TO DATABASE
            statement_data = {
                'user_id': user_id,
                'file_name': file.filename,
                'file_type': file_ext,
                'bank_name': metadata.get('bank_name', 'Unknown'),
                'account_number': metadata.get('account_number', ''),
                'statement_period_start': metadata.get('period_start'),
                'statement_period_end': metadata.get('period_end'),
                'opening_balance': metadata.get('opening_balance'),
                'closing_balance': metadata.get('closing_balance'),
                'transaction_count': len(transactions),
                'parsing_status': 'success' if transactions else 'partial'
            }
            
            logger.info(f"🔵 Saving statement to database...")
            stmt_result = supabase.table('bank_statements').insert(statement_data).execute()
            
            if not stmt_result.data:
                logger.error("❌ Failed to save statement metadata")
                raise HTTPException(status_code=500, detail="Failed to save statement metadata")
            
            statement_id = stmt_result.data[0]['id']
            logger.info(f"✅ Statement saved with ID: {statement_id}")
            
            # 5️⃣ SAVE TRANSACTIONS TO DATABASE
            if transactions:
                # 🚨 CRITICAL: Pre-validate amounts before database insertion
                reasonable_max = 100_000_000.00  # ₦100M sanity check
                
                # Prepare transactions for insertion
                trans_to_insert = []
                for idx, trans in enumerate(transactions):
                    # Cap amounts before inserting
                    debit = float(trans.get('debit_amount', 0))
                    credit = float(trans.get('credit_amount', 0))
                    balance = float(trans.get('balance', 0))
                    
                    # 🚨 VALIDATION: Flag suspicious amounts
                    if abs(debit) > reasonable_max or abs(credit) > reasonable_max:
                        logger.error(
                            f"🚨 TRANSACTION {idx+1} HAS SUSPICIOUS AMOUNT: "
                            f"Debit={debit:,.2f}, Credit={credit:,.2f} - SKIPPING"
                        )
                        continue  # Skip this transaction entirely
                    
                    # Ensure amounts are within limits
                    debit = min(debit, 9999999999999.99)
                    credit = min(credit, 9999999999999.99)
                    balance = min(balance, 9999999999999.99)
                    
                    # Clean description and reference to avoid SQL issues
                    description = str(trans.get('description', '')).strip()
                    if not description:
                        description = "No description provided"  # Default value since column is NOT NULL
                    
                    reference = str(trans.get('reference', '')).strip()
                    if not reference:
                        reference = None  # This column is nullable
                    
                    # Ensure transaction_date is valid
                    trans_date = trans.get('transaction_date', '')
                    if not trans_date:
                        # Use today's date if missing
                        trans_date = datetime.now().strftime('%Y-%m-%d')
                    
                    # Format the date properly
                    try:
                        # Convert to ISO format if needed
                        if 'T' in trans_date:
                            trans_date = trans_date.split('T')[0]
                    except:
                        trans_date = datetime.now().strftime('%Y-%m-%d')
                    
                    trans_to_insert.append({
                        'user_id': user_id,
                        'bank_statement_id': statement_id,
                        'transaction_date': trans_date,
                        'description': description[:255],  # Ensure it fits in text column
                        'reference': reference[:100] if reference else None,
                        'debit_amount': str(debit),  # Convert to string for decimal
                        'credit_amount': str(credit),
                        'balance': str(balance),
                        'is_manually_categorized': False,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    })
                
                logger.info(f"🔵 Saving {len(trans_to_insert)} transactions...")
                logger.info(f"🔵 Sample transaction: {trans_to_insert[0] if trans_to_insert else 'No transactions'}")
                
                # Insert in smaller batches to avoid issues
                batch_size = 10  # Reduced for safety
                successful_inserts = 0
                
                for i in range(0, len(trans_to_insert), batch_size):
                    batch = trans_to_insert[i:i + batch_size]
                    try:
                        logger.info(f"🔵 Inserting batch {i//batch_size + 1} of {(len(trans_to_insert)-1)//batch_size + 1}")
                        
                        # Convert decimal amounts to strings for JSON serialization
                        for item in batch:
                            for amount_field in ['debit_amount', 'credit_amount', 'balance']:
                                if amount_field in item and isinstance(item[amount_field], (int, float)):
                                    item[amount_field] = str(item[amount_field])
                        
                        trans_result = supabase.table('transactions').insert(batch).execute()
                        
                        if not trans_result.data:
                            logger.warning(f"⚠️ Batch {i//batch_size + 1} insert returned no data")
                        else:
                            successful_inserts += len(trans_result.data)
                            logger.info(f"✅ Batch {i//batch_size + 1}: Saved {len(trans_result.data)} transactions")
                            
                    except Exception as batch_error:
                        logger.error(f"❌ Batch {i//batch_size + 1} insert failed: {str(batch_error)}")
                        
                        # Log the error response if available
                        if hasattr(batch_error, 'message'):
                            logger.error(f"❌ Error message: {batch_error.message}")
                        if hasattr(batch_error, 'details'):
                            logger.error(f"❌ Error details: {batch_error.details}")
                        
                        # Try inserting one by one to identify the problematic transaction
                        logger.info("🔄 Trying to insert transactions one by one...")
                        for j, single_trans in enumerate(batch):
                            try:
                                # Ensure all decimal fields are strings
                                for amount_field in ['debit_amount', 'credit_amount', 'balance']:
                                    if amount_field in single_trans and isinstance(single_trans[amount_field], (int, float)):
                                        single_trans[amount_field] = str(single_trans[amount_field])
                                
                                single_result = supabase.table('transactions').insert(single_trans).execute()
                                if single_result.data:
                                    successful_inserts += 1
                                    logger.info(f"  ✅ Transaction {j+1} saved")
                                else:
                                    logger.warning(f"  ⚠️ Transaction {j+1} failed - no data returned")
                            except Exception as single_error:
                                logger.error(f"  ❌ Transaction {j+1} error: {str(single_error)}")
                                # Don't log the full transaction to avoid PII in logs
                                logger.error(f"  ❌ Problem with transaction date: {single_trans.get('transaction_date')}, description: {single_trans.get('description')[:50]}")
                
                logger.info(f"✅ Saved {successful_inserts}/{len(transactions)} transactions")
            
            # 6️⃣ TRIGGER CATEGORIZATION IN BACKGROUND (optional)
            if background_tasks and len(transactions) > 0:
                background_tasks.add_task(
                    auto_categorize_transactions,
                    statement_id=statement_id,
                    supabase_client=supabase
                )
                logger.info("🔵 Background categorization queued")
            
            return BankStatementUploadResponse(
                success=True,
                statement_id=statement_id,
                file_name=file.filename,
                transaction_count=len(transactions),
                parsing_status='success',
                message=f"Successfully parsed {len(transactions)} transactions",
                metadata=metadata
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                logger.info(f"🔵 Cleaned up temp file")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ UPLOAD FAILED: {str(e)}")
        logger.error(f"Stack trace:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# =====================================================
# 8️⃣ UPLOAD STATUS CHECK
# =====================================================

@router.get("/upload-status/{statement_id}")
async def check_upload_status(
    statement_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📊 Check if upload and background tasks are complete
    """
    try:
        user_id = current_user['id']
        
        # Check if statement exists
        stmt_result = supabase.table('bank_statements')\
            .select('*')\
            .eq('id', statement_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        if not stmt_result.data:
            return {"success": False, "error": "Statement not found"}
        
        statement = stmt_result.data
        
        # Check if categorization is complete
        trans_result = supabase.table('transactions')\
            .select('account_code', count='exact')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .execute()
        
        total_result = supabase.table('transactions')\
            .select('id', count='exact')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .execute()
        
        categorized_count = trans_result.count or 0
        total_count = total_result.count or 0
        
        return {
            "success": True,
            "statement_id": statement_id,
            "parsing_status": statement.get('parsing_status', 'unknown'),
            "transaction_count": total_count,
            "categorized_count": categorized_count,
            "categorization_complete": categorized_count == total_count and total_count > 0,
            "percentage": round((categorized_count / total_count * 100) if total_count > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"❌ Upload status check failed: {str(e)}")
        return {"success": False, "error": str(e)}
    
# =====================================================
# 2️⃣ TRANSACTION CATEGORIZATION
# =====================================================

@router.post("/categorize-transactions")
async def categorize_transactions(
    request: TransactionCategorizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    🤖 Categorize transactions using AI or rule-based engine
    
    **Methods:**
    - AI: Groq (FREE) or Claude-powered categorization
    - Rules: Keyword-based categorization (fallback)
    """
    try:
        user_id = current_user['id']
        statement_id = request.statement_id
        
        # 1️⃣ FETCH UNCATEGORIZED TRANSACTIONS
        trans_result = supabase.table('transactions')\
            .select('*')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .is_('account_code', 'null')\
            .execute()
        
        if not trans_result.data:
            return {
                "success": True,
                "message": "No uncategorized transactions found",
                "categorized_count": 0
            }
        
        transactions = trans_result.data
        
        # 2️⃣ CATEGORIZE USING AI OR RULES
        from backend.services.bookkeeping.categorization_service import TransactionCategorizer
        
        # Get API keys from environment
        import os
        groq_key = os.environ.get('GROQ_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        
        categorizer = TransactionCategorizer(
            groq_api_key=groq_key,
            anthropic_api_key=anthropic_key
        )
        
        # Convert transactions to format expected by categorizer
        trans_for_categorization = []
        for trans in transactions:
            trans_for_categorization.append({
                'transaction_date': trans.get('transaction_date'),
                'description': trans.get('description', ''),
                'debit_amount': trans.get('debit_amount', 0),
                'credit_amount': trans.get('credit_amount', 0),
                'id': trans.get('id')  # Keep ID for updating
            })
        
        # Categorize
        categorized = await categorizer.categorize_batch(
            transactions=trans_for_categorization,
            use_ai=request.use_ai and (groq_key or anthropic_key)
        )
        
        # 3️⃣ UPDATE TRANSACTIONS IN DATABASE
        update_count = 0
        for trans in categorized:
            # Find the transaction by ID
            if 'id' in trans:
                update_result = supabase.table('transactions')\
                    .update({
                        'account_code': trans.get('account_code', ''),
                        'category': trans.get('category', ''),
                        'confidence_score': trans.get('confidence_score', 0.5),
                        'is_manually_categorized': trans.get('is_manually_categorized', False)
                    })\
                    .eq('id', trans['id'])\
                    .execute()
                
                if update_result.data:
                    update_count += 1
        
        logger.info(f"✅ Categorized {update_count}/{len(transactions)} transactions")
        
        return {
            "success": True,
            "message": f"Categorized {update_count} transactions",
            "categorized_count": update_count,
            "method": "AI" if (request.use_ai and (groq_key or anthropic_key)) else "Rules"
        }
        
    except Exception as e:
        logger.error(f"❌ Categorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

# =====================================================
# 3️⃣ MANUAL TRANSACTION UPDATE
# =====================================================

@router.put("/transactions/update")
async def update_transaction_category(
    request: TransactionUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    ✏️ Manually update transaction category
    
    **Use Case:** User corrects AI categorization
    """
    try:
        user_id = current_user['id']
        
        # Update transaction
        result = supabase.table('transactions')\
            .update({
                'account_code': request.account_code,
                'category': request.category,
                'is_manually_categorized': True,
                'categorization_notes': request.notes,
                'confidence_score': 1.0  # Manual = 100% confidence
            })\
            .eq('id', request.transaction_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        logger.info(f"✅ Transaction {request.transaction_id} updated manually")
        
        return {
            "success": True,
            "message": "Transaction category updated",
            "transaction": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transaction update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 4️⃣ TRIAL BALANCE GENERATION
# =====================================================

@router.post("/trial-balance/generate")
async def generate_trial_balance(
    request: TrialBalanceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📊 Generate trial balance report for a period
    
    **Output:** JSON report with:
    - Account-level debits/credits
    - Total debits/credits
    - Balance status (balanced/unbalanced)
    """
    try:
        user_id = current_user['id']
        
        # Generate trial balance
        from backend.services.bookkeeping.trial_balance_service import TrialBalanceGenerator
        
        tb_generator = TrialBalanceGenerator(supabase)
        
        result = await tb_generator.generate(
            user_id=user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            save_to_db=request.save_report
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        logger.info(f"✅ Trial balance generated for user {user_id}")
        
        return {
            "success": True,
            "trial_balance": result['trial_balance'],
            "report_id": result.get('report_id'),
            "validation": tb_generator.validate_trial_balance(result['trial_balance'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Trial balance generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 5️⃣ TRIAL BALANCE EXPORT TO EXCEL
# =====================================================

@router.post("/trial-balance/export")
async def export_trial_balance_to_excel(
    request: TrialBalanceExportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📥 Export trial balance to Excel file
    
    **Options:**
    - Use existing report_id, OR
    - Generate new report for period_start/period_end
    """
    try:
        user_id = current_user['id']
        trial_balance_data = None
        
        # 1️⃣ GET TRIAL BALANCE DATA
        if request.report_id:
            # Fetch existing report
            result = supabase.table('trial_balances')\
                .select('report_data')\
                .eq('id', request.report_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Report not found")
            
            trial_balance_data = result.data['report_data']
        
        elif request.period_start and request.period_end:
            # Generate new report
            from backend.services.bookkeeping import TrialBalanceGenerator
            
            tb_generator = TrialBalanceGenerator(supabase)
            result = await tb_generator.generate(
                user_id=user_id,
                period_start=request.period_start,
                period_end=request.period_end,
                save_to_db=False
            )
            
            if not result['success']:
                raise HTTPException(status_code=500, detail="Failed to generate trial balance")
            
            trial_balance_data = result['trial_balance']
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either report_id or (period_start + period_end) required"
            )
        
        # 2️⃣ GENERATE EXCEL FILE
        from backend.services.bookkeeping.exporter_service import BookkeepingExporter
        
        exporter = BookkeepingExporter()
        excel_bytes = exporter.export_trial_balance_to_excel(
            trial_balance=trial_balance_data,
            company_name=request.company_name
        )
        
        # 3️⃣ RETURN AS DOWNLOADABLE FILE
        filename = f"trial_balance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Excel export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 6️⃣ GET USER'S BANK STATEMENTS
# =====================================================

@router.get("/statements")
async def get_bank_statements(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📋 Get user's uploaded bank statements
    """
    try:
        user_id = current_user['id']
        
        result = supabase.table('bank_statements')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "statements": result.data if result.data else []
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch statements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 7️⃣ GET TRANSACTIONS FOR A STATEMENT
# =====================================================

@router.get("/statements/{statement_id}/transactions")
async def get_statement_transactions(
    statement_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📋 Get all transactions for a bank statement
    """
    try:
        user_id = current_user['id']
        
        result = supabase.table('transactions')\
            .select('*')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .order('transaction_date', desc=False)\
            .execute()
        
        return {
            "success": True,
            "transactions": result.data if result.data else []
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 🚨 ADD THIS NEW CODE BLOCK RIGHT HERE:
# =====================================================

@router.get("/upload-status/{statement_id}")
async def check_upload_status(
    statement_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    📊 Check if upload and background tasks are complete
    """
    try:
        user_id = current_user['id']
        
        # Check if statement exists
        stmt_result = supabase.table('bank_statements')\
            .select('*')\
            .eq('id', statement_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        if not stmt_result.data:
            return {"success": False, "error": "Statement not found"}
        
        statement = stmt_result.data
        
        # Check if categorization is complete
        trans_result = supabase.table('transactions')\
            .select('account_code', count='exact')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .execute()
        
        total_result = supabase.table('transactions')\
            .select('id', count='exact')\
            .eq('bank_statement_id', statement_id)\
            .eq('user_id', user_id)\
            .execute()
        
        categorized_count = trans_result.count or 0
        total_count = total_result.count or 0
        
        return {
            "success": True,
            "statement_id": statement_id,
            "parsing_status": statement.get('parsing_status', 'unknown'),
            "transaction_count": total_count,
            "categorized_count": categorized_count,
            "categorization_complete": categorized_count == total_count and total_count > 0,
            "percentage": round((categorized_count / total_count * 100) if total_count > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"❌ Upload status check failed: {str(e)}")
        return {"success": False, "error": str(e)}

# =====================================================
# BACKGROUND TASKS
# =====================================================

async def auto_categorize_transactions(statement_id: str, supabase_client: Client):
    """
    Background task to automatically categorize transactions
    """
    try:
        logger.info(f"🤖 Auto-categorizing transactions for statement {statement_id}")
        
        # Fetch transactions
        trans_result = supabase_client.table('transactions')\
            .select('*')\
            .eq('bank_statement_id', statement_id)\
            .execute()
        
        if not trans_result.data:
            return
        
        # Categorize using rules (no AI key needed)
        from backend.services.bookkeeping import TransactionCategorizer
        
        categorizer = TransactionCategorizer()
        categorized = await categorizer.categorize_batch(
            transactions=trans_result.data,
            use_ai=False  # Use rules for background task
        )
        
        # Update transactions
        for trans in categorized:
            supabase_client.table('transactions')\
                .update({
                    'account_code': trans.get('account_code'),
                    'category': trans.get('category'),
                    'confidence_score': trans.get('confidence_score')
                })\
                .eq('id', trans['id'])\
                .execute()
        
        logger.info(f"✅ Auto-categorized {len(categorized)} transactions")
        
    except Exception as e:
        logger.error(f"❌ Auto-categorization failed: {str(e)}")

@router.post("/test-parser")
async def test_parser_directly(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    🔧 Direct parser testing endpoint (for debugging)
    """
    try:
        # Save file temporarily
        file_ext = file.filename.split('.')[-1].lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Initialize parser
        from backend.services.bookkeeping.parser_service import BankStatementParser
        parser = BankStatementParser()
        
        # Extract text
        if file_ext == 'pdf':
            text = parser._extract_pdf_text(tmp_file_path)
            
            # Show first 1000 chars
            result = {
                "text_length": len(text),
                "text_preview": text[:1000],
                "lines_found": []
            }
            
            # Find transaction-like lines
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if len(line) > 20 and any(x in line for x in ['Jan-', 'Feb-', 'Mar-', 'Apr-', 'May-']):
                    result["lines_found"].append({
                        "line_number": i,
                        "content": line[:150]
                    })
            
            # Try to parse
            parse_result = parser.parse_file(tmp_file_path, file_ext)
            result["parse_result"] = parse_result
            
            # Clean up
            os.unlink(tmp_file_path)
            
            return result
            
    except Exception as e:
        return {"error": str(e)}
    
@router.post("/test-trial-balance")
async def test_trial_balance_service(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Test trial balance service directly"""
    try:
        user_id = current_user['id']
        
        from backend.services.bookkeeping.trial_balance_service import TrialBalanceGenerator
        
        tb_generator = TrialBalanceGenerator(supabase)
        
        # Test with a simple date range
        from datetime import date
        test_result = await tb_generator.generate(
            user_id=user_id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            save_to_db=False
        )
        
        logger.info(f"🔵 Test result: {test_result}")
        
        return test_result
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    
@router.get("/debug/user-info")
async def debug_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Get current user info for debugging"""
    try:
        user_id = current_user['id']
        email = current_user.get('email', 'No email')
        
        # Check transaction counts
        all_trans = supabase.table('transactions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        
        categorized_trans = supabase.table('transactions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .execute()
        
        # Get date range
        date_range = supabase.table('transactions')\
            .select('transaction_date')\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .order('transaction_date')\
            .limit(1)\
            .execute()
        
        earliest_date = None
        latest_date = None
        
        if date_range.data and len(date_range.data) > 0:
            earliest_date = date_range.data[0].get('transaction_date')
        
        date_range_end = supabase.table('transactions')\
            .select('transaction_date')\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .order('transaction_date', desc=True)\
            .limit(1)\
            .execute()
        
        if date_range_end.data and len(date_range_end.data) > 0:
            latest_date = date_range_end.data[0].get('transaction_date')
        
        return {
            "success": True,
            "user_info": {
                "user_id": user_id,
                "email": email,
                "total_transactions": all_trans.count or 0,
                "categorized_transactions": categorized_trans.count or 0,
                "categorized_percentage": round((categorized_trans.count / all_trans.count * 100) if all_trans.count > 0 else 0, 1),
                "earliest_categorized_date": earliest_date,
                "latest_categorized_date": latest_date
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Debug endpoint failed: {str(e)}")
        return {"success": False, "error": str(e)}
    
@router.post("/simple-trial-balance")
async def simple_trial_balance(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Generate trial balance from ALL categorized transactions (no date filter)"""
    try:
        user_id = current_user['id']
        
        # Get ALL categorized transactions
        result = supabase.table('transactions')\
            .select('*')\
            .eq('user_id', user_id)\
            .not_.is_('account_code', 'null')\
            .execute()
        
        if not result.data:
            return {"success": False, "error": "No categorized transactions found"}
        
        transactions = result.data
        logger.info(f"✅ Found {len(transactions)} categorized transactions")
        
        # Simple aggregation
        accounts = {}
        for trans in transactions:
            account_code = trans.get('account_code', '0000')
            if account_code not in accounts:
                accounts[account_code] = {
                    'account_code': account_code,
                    'account_name': trans.get('category', 'Unknown'),
                    'debits': 0.0,
                    'credits': 0.0
                }
            
            # Convert amounts safely
            debit = float(trans.get('debit_amount', 0) or 0)
            credit = float(trans.get('credit_amount', 0) or 0)
            
            accounts[account_code]['debits'] += debit
            accounts[account_code]['credits'] += credit
        
        # Prepare response
        accounts_list = []
        total_debits = 0.0
        total_credits = 0.0
        
        for acc_code, acc in accounts.items():
            balance = acc['debits'] - acc['credits']
            accounts_list.append({
                'account_code': acc_code,
                'account_name': acc['account_name'],
                'account_type': 'Asset' if acc_code.startswith('1') else 
                               'Liability' if acc_code.startswith('2') else 
                               'Equity' if acc_code.startswith('3') else 
                               'Revenue' if acc_code.startswith('4') else 
                               'Expense',
                'debits': acc['debits'],
                'credits': acc['credits'],
                'balance': balance
            })
            
            total_debits += acc['debits']
            total_credits += acc['credits']
        
        # Get actual date range
        dates = [t.get('transaction_date') for t in transactions if t.get('transaction_date')]
        period_start = min(dates) if dates else '2024-01-01'
        period_end = max(dates) if dates else '2024-12-31'
        
        trial_balance = {
            'accounts': accounts_list,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': abs(total_debits - total_credits) < 0.01,
            'period_start': period_start,
            'period_end': period_end
        }
        
        return {
            "success": True,
            "trial_balance": trial_balance,
            "transaction_count": len(transactions)
        }
        
    except Exception as e:
        logger.error(f"❌ Simple trial balance failed: {str(e)}")
        return {"success": False, "error": str(e)}