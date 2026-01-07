# backend/services/bookkeeping/export_service.py
"""
Bookkeeping Export Service - Generate Excel files
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import io
import pandas as pd
from decimal import Decimal

logger = logging.getLogger(__name__)

class BookkeepingExporter:
    """
    Export bookkeeping data to Excel format
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize exporter
        
        Note: Supabase client optional - used for uploading files to storage
        """
        self.supabase = supabase_client
    
    def export_trial_balance_to_excel(
        self,
        trial_balance: Dict,
        company_name: str = "Your Company",
        include_charts: bool = False
    ) -> bytes:
        """
        Export trial balance to Excel file
        
        Args:
            trial_balance: Trial balance data from generator
            company_name: Company name for header
            include_charts: Whether to include visual charts (future)
        
        Returns:
            Excel file as bytes
        """
        try:
            # Prepare data for Excel
            accounts_data = trial_balance.get('accounts', [])
            
            # Convert to DataFrame
            df = pd.DataFrame(accounts_data)
            
            # Rename columns for clarity
            column_map = {
                'account_code': 'Account Code',
                'account_name': 'Account Name',
                'account_type': 'Type',
                'debits': 'Debits (₦)',
                'credits': 'Credits (₦)',
                'balance': 'Balance (₦)'
            }
            df = df.rename(columns=column_map)
            
            # Format currency columns
            for col in ['Debits (₦)', 'Credits (₦)', 'Balance (₦)']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{float(x):,.2f}" if pd.notna(x) else "0.00")
            
            # Create Excel file in memory
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Get workbook and worksheet objects
                workbook = writer.book
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#4CAF50',
                    'font_color': 'white'
                })
                
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 16,
                    'align': 'center'
                })
                
                subtitle_format = workbook.add_format({
                    'font_size': 11,
                    'align': 'center',
                    'italic': True
                })
                
                column_header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#E8F5E9',
                    'border': 1
                })
                
                number_format = workbook.add_format({
                    'num_format': '#,##0.00',
                    'border': 1
                })
                
                text_format = workbook.add_format({
                    'border': 1
                })
                
                total_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#FFF9C4',
                    'border': 1,
                    'num_format': '#,##0.00'
                })
                
                # Write to Excel
                df.to_excel(writer, sheet_name='Trial Balance', index=False, startrow=4)
                
                worksheet = writer.sheets['Trial Balance']
                
                # Add title
                worksheet.merge_range('A1:F1', f"{company_name}", title_format)
                worksheet.merge_range('A2:F2', "TRIAL BALANCE", subtitle_format)
                
                # Add period
                period_start = trial_balance.get('period_start', '')
                period_end = trial_balance.get('period_end', '')
                period_text = f"Period: {period_start} to {period_end}"
                worksheet.merge_range('A3:F3', period_text, subtitle_format)
                
                # Format column headers
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(4, col_num, value, column_header_format)
                
                # Set column widths
                worksheet.set_column('A:A', 15)  # Account Code
                worksheet.set_column('B:B', 35)  # Account Name
                worksheet.set_column('C:C', 15)  # Type
                worksheet.set_column('D:D', 18)  # Debits
                worksheet.set_column('E:E', 18)  # Credits
                worksheet.set_column('F:F', 18)  # Balance
                
                # Add totals row
                last_row = len(df) + 5
                worksheet.write(last_row, 2, "TOTAL:", total_format)
                
                total_debits = trial_balance.get('total_debits', 0)
                total_credits = trial_balance.get('total_credits', 0)
                
                worksheet.write(last_row, 3, float(total_debits), total_format)
                worksheet.write(last_row, 4, float(total_credits), total_format)
                
                # Add balance status
                is_balanced = trial_balance.get('is_balanced', False)
                balance_status = "✓ BALANCED" if is_balanced else "⚠ NOT BALANCED"
                
                status_format = workbook.add_format({
                    'bold': True,
                    'font_color': 'green' if is_balanced else 'red',
                    'align': 'center',
                    'font_size': 12
                })
                
                worksheet.merge_range(f'A{last_row+2}:F{last_row+2}', balance_status, status_format)
                
                # Add generation timestamp
                timestamp_format = workbook.add_format({
                    'italic': True,
                    'font_size': 9,
                    'align': 'right'
                })
                
                generated_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
                worksheet.merge_range(
                    f'A{last_row+4}:F{last_row+4}',
                    f"Generated: {generated_at}",
                    timestamp_format
                )
            
            # Get the Excel file as bytes
            excel_bytes = output.getvalue()
            
            logger.info(f"✅ Excel file generated: {len(excel_bytes)} bytes")
            return excel_bytes
            
        except Exception as e:
            logger.error(f"❌ Excel export failed: {str(e)}")
            raise
    
    def export_transactions_to_excel(
        self,
        transactions: list,
        filename: str = "transactions.xlsx"
    ) -> bytes:
        """
        Export transactions to Excel file
        
        Simpler format than trial balance
        """
        try:
            df = pd.DataFrame(transactions)
            
            # Prepare columns
            columns_to_export = [
                'transaction_date',
                'description',
                'reference',
                'debit_amount',
                'credit_amount',
                'balance',
                'category',
                'account_code'
            ]
            
            df = df[columns_to_export]
            
            # Rename for clarity
            df.columns = [
                'Date',
                'Description',
                'Reference',
                'Debit (₦)',
                'Credit (₦)',
                'Balance (₦)',
                'Category',
                'Account'
            ]
            
            # Create Excel
            output = io.BytesIO()
            df.to_excel(output, index=False, sheet_name='Transactions')
            
            excel_bytes = output.getvalue()
            
            logger.info(f"✅ Transactions exported: {len(transactions)} rows")
            return excel_bytes
            
        except Exception as e:
            logger.error(f"❌ Transactions export failed: {str(e)}")
            raise
    
    async def upload_to_storage(
        self,
        file_bytes: bytes,
        filename: str,
        bucket_name: str = 'bookkeeping-exports'
    ) -> Optional[str]:
        """
        Upload Excel file to Supabase storage
        
        Returns:
            Public URL of uploaded file, or None if failed
        """
        if not self.supabase:
            logger.warning("⚠️ Supabase client not configured")
            return None
        
        try:
            # Upload to storage
            result = self.supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            )
            
            if result:
                # Get public URL
                public_url = self.supabase.storage.from_(bucket_name).get_public_url(filename)
                logger.info(f"✅ File uploaded: {public_url}")
                return public_url
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Storage upload failed: {str(e)}")
            return None