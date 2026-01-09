# backend/services/bookkeeping/parser_service.py
"""
Bank Statement Parser - Handles CSV, Excel, PDF uploads
"""

import re
import pandas as pd
import PyPDF2
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

# Try to import pdfplumber
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger(__name__)

class BankStatementParser:
    """
    Parse bank statements from multiple formats (CSV, Excel, PDF)
    """
    
    # Common Nigerian bank statement headers
    COMMON_HEADERS = {
        'date': ['date', 'transaction date', 'trans date', 'posting date', 'value date'],
        'description': ['description', 'narration', 'details', 'transaction details', 'particulars'],
        'debit': ['debit', 'debit amount', 'withdrawal', 'dr', 'debits', 'pay out'],
        'credit': ['credit', 'credit amount', 'deposit', 'cr', 'credits', 'pay in'],
        'balance': ['balance', 'running balance', 'closing balance', 'book balance'],
        'reference': ['reference', 'ref', 'transaction ref', 'ref no']
    }
    
    def __init__(self):
        self.supported_formats = ['csv', 'xlsx', 'xls', 'pdf']
    
    def parse_file(self, file_path: str, file_type: str) -> Dict:
        """
        Main entry point - parse any supported file type
        """
        try:
            if file_type == 'csv':
                return self._parse_csv(file_path)
            elif file_type in ['xlsx', 'xls']:
                return self._parse_excel(file_path)
            elif file_type == 'pdf':
                return self._parse_pdf(file_path)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_type}'
                }
        except Exception as e:
            logger.error(f"❌ Parsing failed: {str(e)}")
            return {
                'success': False,
                'error': f'Parsing failed: {str(e)}'
            }
    
    def _parse_csv(self, file_path: str) -> Dict:
        """Parse CSV bank statement"""
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not decode CSV file with any encoding")
            
            df = self._normalize_columns(df)
            transactions = self._extract_transactions(df)
            metadata = self._extract_metadata(df)
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ CSV parsing error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_excel(self, file_path: str) -> Dict:
        """Parse Excel bank statement"""
        try:
            df = pd.read_excel(file_path)
            df = self._normalize_columns(df)
            transactions = self._extract_transactions(df)
            metadata = self._extract_metadata(df)
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Excel parsing error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_pdf(self, file_path: str) -> Dict:
        """
        Main PDF parser with multiple strategies
        """
        # First try direct Fidelity Bank parser
        try:
            result = self._parse_fidelity_pdf_direct(file_path)
            if result['success'] and len(result.get('transactions', [])) > 0:
                logger.info(f"✅ Fidelity direct parser extracted {len(result['transactions'])} transactions")
                return result
        except Exception as e:
            logger.warning(f"⚠️ Fidelity direct parser failed: {e}")
        # Try pdfplumber with table extraction first
        if PDFPLUMBER_AVAILABLE:
            try:
                result = self._parse_pdf_with_pdfplumber_enhanced(file_path)
                if result['success'] and len(result.get('transactions', [])) > 0:
                    logger.info(f"✅ pdfplumber extracted {len(result['transactions'])} transactions")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ pdfplumber enhanced failed: {e}")
        
        # Fallback to PyPDF2 with enhanced parsing
        try:
            text = self._extract_pdf_text(file_path)
            
            if not text or len(text.strip()) < 50:
                return {
                    'success': False,
                    'error': 'PDF text extraction failed or PDF appears to be scanned/image-based'
                }
            
            logger.info(f"🔵 Extracted {len(text)} characters from PDF")
            
            # Extract metadata first
            metadata = self._extract_metadata_from_pdf_text(text)
            
            # Try enhanced text extraction
            transactions = self._extract_transactions_from_pdf_text_enhanced(text)
            
            if transactions:
                return {
                    'success': True,
                    'transactions': transactions,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'No transactions could be extracted from PDF text'
                }
                
        except Exception as e:
            logger.error(f"❌ PDF parsing error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_pdf_with_pdfplumber_enhanced(self, file_path: str) -> Dict:
        """Enhanced PDF parsing using pdfplumber with better table detection"""
        try:
            transactions = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Try to extract tables
                    tables = page.extract_tables()
                    
                    # If no tables found, try to extract with custom settings
                    if not tables:
                        # Extract text and try to parse
                        text = page.extract_text()
                        if text:
                            page_transactions = self._parse_table_from_text(text)
                            transactions.extend(page_transactions)
                        continue
                    
                    # Process each table
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Find header row (look for column names)
                        header_row = 0
                        for i, row in enumerate(table):
                            if row and any(col for col in row if col and 'date' in str(col).lower()):
                                header_row = i
                                break
                        
                        # Process rows after header
                        for row_idx in range(header_row + 1, len(table)):
                            row = table[row_idx]
                            if not row or len(row) < 3:
                                continue
                            
                            try:
                                transaction = self._parse_table_row(row)
                                if transaction:
                                    transactions.append(transaction)
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to parse row {row_idx}: {e}")
                                continue
            
            if transactions:
                return {
                    'success': True,
                    'transactions': transactions,
                    'metadata': self._extract_metadata_from_pdf_text(self._extract_pdf_text(file_path))
                }
            else:
                return {'success': False, 'error': 'No transactions found in PDF tables'}
                
        except Exception as e:
            logger.error(f"❌ Enhanced pdfplumber parsing failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_table_row(self, row: List) -> Optional[Dict]:
        """Parse a table row into transaction dict"""
        # Skip empty rows
        if not row or not any(cell for cell in row if cell and str(cell).strip()):
            return None
        
        # Clean row cells
        row = [str(cell).strip() if cell else '' for cell in row]
        
        # Look for date in first few columns
        date_str = None
        date_idx = -1
        
        for i, cell in enumerate(row[:3]):
            if cell and self._is_date_string(cell):
                date_str = cell
                date_idx = i
                break
        
        if not date_str:
            return None
        
        # Parse date
        trans_date = self._parse_date(date_str)
        if not trans_date:
            return None
        
        # Look for amounts in the row
        amounts = []
        for cell in row:
            if cell and self._looks_like_amount(cell):
                amounts.append(self._clean_amount(cell))
        
        if not amounts:
            return None
        
        # Extract description
        description = ''
        if date_idx + 1 < len(row):
            # Try to get description from cells after date
            desc_parts = []
            for i in range(date_idx + 1, len(row)):
                cell = row[i]
                if cell and not self._looks_like_amount(cell) and not self._is_date_string(cell):
                    desc_parts.append(cell)
            description = ' '.join(desc_parts).strip()
        
        # Determine debit/credit
        # In bank statements, usually:
        # - Debit (withdrawal) is positive amount that reduces balance
        # - Credit (deposit) is positive amount that increases balance
        # We'll determine based on context
        
        if len(amounts) >= 2:
            # Usually transaction amount and balance
            transaction_amount = amounts[0]
            balance_amount = amounts[-1]
            
            # Try to determine from description
            desc_lower = description.lower()
            if any(word in desc_lower for word in ['fee', 'charge', 'withdrawal', 'debit']):
                debit = transaction_amount
                credit = 0
            elif any(word in desc_lower for word in ['transfer', 'deposit', 'credit']):
                debit = 0
                credit = transaction_amount
            else:
                # Default: assume debit for expenses
                debit = transaction_amount
                credit = 0
        else:
            debit = 0
            credit = amounts[0]
            balance_amount = 0
        
        return {
            'transaction_date': trans_date.strftime('%Y-%m-%d'),
            'description': description,
            'reference': '',
            'debit_amount': debit,
            'credit_amount': credit,
            'balance': balance_amount
        }
    
    def _parse_table_from_text(self, text: str) -> List[Dict]:
        """Parse table structure from extracted text"""
        transactions = []
        lines = text.split('\n')
        
        # Find transaction section
        in_transaction_section = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Look for transaction section start
            if 'transaction date' in line.lower() or any(date in line.lower() for date in ['opening', '8-jan-24', '23-jan-24']):
                in_transaction_section = True
                continue
            
            if not in_transaction_section:
                continue
            
            # Skip header lines
            if any(word in line.lower() for word in ['date', 'value', 'channel', 'details', 'balance']):
                continue
            
            # Skip summary lines
            if any(word in line.lower() for word in ['closing', 'total', 'page', 'of']):
                continue
            
            # Try to parse transaction line
            transaction = self._parse_fidelity_transaction_line(line)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _parse_fidelity_transaction_line(self, line: str) -> Optional[Dict]:
        """Parse Fidelity Bank specific transaction line"""
        # Example lines:
        # "8-Jan-24    8-Jan-24    Others    Q3 Visa Card Mice Fee 2023    50.00    4,950.82"
        # "23-Jan-24    23-Jan-24    NIP Transfer    PWAN PERFECTION/Felting work for 5 Units@Paradiso    1,600,000.00    1,604,900.82"
        
        # Split by multiple spaces
        parts = re.split(r'\s{2,}', line)
        if len(parts) < 4:
            return None
        
        # First part should be date
        date_str = parts[0]
        trans_date = self._parse_date(date_str)
        if not trans_date:
            return None
        
        # Find amounts in the line
        amounts = []
        amount_positions = []
        
        for i, part in enumerate(parts):
            if self._looks_like_amount(part):
                amounts.append(self._clean_amount(part))
                amount_positions.append(i)
        
        if not amounts:
            return None
        
        # Get description
        description = ''
        if len(amount_positions) > 0:
            # Everything between date and first amount is description
            desc_start = 1  # Skip date
            desc_end = amount_positions[0]
            description_parts = parts[desc_start:desc_end]
            description = ' '.join(description_parts).strip()
        
        # Determine debit/credit
        # In Fidelity statements:
        # - If there's "Pay In" column, it's credit
        # - If there's "Pay Out" column, it's debit
        # - Last amount is usually balance
        
        transaction_amount = amounts[0]
        balance_amount = amounts[-1] if len(amounts) > 1 else 0
        
        # Check if it's likely a debit (expense)
        line_lower = line.lower()
        is_likely_debit = any(word in line_lower for word in [
            'fee', 'charge', 'debit', 'withdrawal', 'payment',
            'sms', 'alert', 'levy', 'transfer to', 'cob trf to'
        ])
        
        is_likely_credit = any(word in line_lower for word in [
            'transfer from', 'deposit', 'credit', 'pay in',
            'received', 'mega bricks', 'investment', 'ighodalo'
        ])
        
        if is_likely_debit:
            debit = transaction_amount
            credit = 0
        elif is_likely_credit:
            debit = 0
            credit = transaction_amount
        else:
            # Default based on amount position
            debit = transaction_amount
            credit = 0
        
        return {
            'transaction_date': trans_date.strftime('%Y-%m-%d'),
            'description': description,
            'reference': '',
            'debit_amount': debit,
            'credit_amount': credit,
            'balance': balance_amount
        }
    
    def _extract_transactions_from_pdf_text_enhanced(self, text: str) -> List[Dict]:
        """Enhanced text extraction for PDF statements"""
        transactions = []
        
        # First try table parsing
        table_transactions = self._parse_table_from_text(text)
        if table_transactions:
            return table_transactions
        
        # Fallback to regex patterns
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) < 20:
                continue
            
            # Skip non-transaction lines
            if any(word in line.lower() for word in ['opening', 'closing', 'page', 'fidelity bank']):
                continue
            
            # Try multiple parsing strategies
            transaction = self._parse_fidelity_transaction_line(line)
            if not transaction:
                # Try alternative parsing
                transaction = self._parse_transaction_line_alternative(line)
            
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _parse_transaction_line_alternative(self, line: str) -> Optional[Dict]:
        """Alternative transaction line parser"""
        # Look for date at beginning
        date_match = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{2,4})', line)
        if not date_match:
            return None
        
        date_str = date_match.group(1)
        trans_date = self._parse_date(date_str)
        if not trans_date:
            return None
        
        # Extract amounts
        amount_pattern = r'([\d,]+\.\d{2})'
        amounts = re.findall(amount_pattern, line)
        if not amounts:
            return None
        
        # Clean amounts
        cleaned_amounts = [self._clean_amount(amt) for amt in amounts]
        
        # Extract description (between date and first amount)
        date_end = date_match.end()
        first_amount_start = line.find(amounts[0])
        
        if first_amount_start > date_end:
            description = line[date_end:first_amount_start].strip()
        else:
            # Try to extract description differently
            parts = line.split()
            desc_parts = []
            in_desc = False
            
            for part in parts:
                if self._is_date_string(part):
                    in_desc = True
                elif self._looks_like_amount(part):
                    break
                elif in_desc:
                    desc_parts.append(part)
            
            description = ' '.join(desc_parts)
        
        # Determine debit/credit
        line_lower = line.lower()
        if any(word in line_lower for word in ['fee', 'charge', 'sms', 'levy', 'trf to']):
            debit = cleaned_amounts[0]
            credit = 0
        else:
            debit = 0
            credit = cleaned_amounts[0]
        
        balance = cleaned_amounts[-1] if len(cleaned_amounts) > 1 else 0
        
        return {
            'transaction_date': trans_date.strftime('%Y-%m-%d'),
            'description': description,
            'reference': '',
            'debit_amount': debit,
            'credit_amount': credit,
            'balance': balance
        }
    
    def _looks_like_amount(self, text: str) -> bool:
        """Check if text looks like a monetary amount"""
        if not text:
            return False
        
        # Remove commas and check
        cleaned = str(text).replace(',', '')
        
        # Check for patterns like 50.00, 1,600,000.00
        patterns = [
            r'^\d+\.\d{2}$',  # 50.00
            r'^\d+\.\d{1}$',  # 50.0 (less common)
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned):
                return True
        
        return False
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace
                text = text.strip()
                
                return text
                
        except Exception as e:
            logger.error(f"❌ PDF text extraction failed: {str(e)}")
            return ""
    
    def _extract_metadata_from_pdf_text(self, text: str) -> Dict:
        """Extract metadata from PDF text"""
        metadata = {}
        
        # Extract account number
        acc_patterns = [
            r'Account[:\s]*(\d{8,})',
            r'Account No[:\s]*(\d{8,})',
            r'Account Number[:\s]*(\d{8,})'
        ]
        
        for pattern in acc_patterns:
            acc_match = re.search(pattern, text, re.IGNORECASE)
            if acc_match:
                metadata['account_number'] = acc_match.group(1)
                break
        
        # Extract bank name
        banks = ['Fidelity Bank', 'GTBank', 'Access', 'Zenith', 'First Bank', 'UBA', 'Stanbic']
        for bank in banks:
            if bank.lower() in text.lower():
                metadata['bank_name'] = bank
                break
        
        # Extract period
        period_patterns = [
            r'From\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+to\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            r'Period[:\s]*(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+to\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})'
        ]
        
        for pattern in period_patterns:
            period_match = re.search(pattern, text, re.IGNORECASE)
            if period_match:
                start_date = self._parse_date(period_match.group(1))
                end_date = self._parse_date(period_match.group(2))
                if start_date:
                    metadata['period_start'] = start_date.strftime('%Y-%m-%d')
                if end_date:
                    metadata['period_end'] = end_date.strftime('%Y-%m-%d')
                break
        
        # Extract opening balance
        opening_patterns = [
            r'Opening Balance\s+([\d,]+\.\d{2})',
            r'Opening Bal[:\s]*([\d,]+\.\d{2})'
        ]
        
        for pattern in opening_patterns:
            opening_match = re.search(pattern, text, re.IGNORECASE)
            if opening_match:
                metadata['opening_balance'] = self._clean_amount(opening_match.group(1))
                break
        
        # Extract closing balance
        closing_patterns = [
            r'Closing Balance\s+([\d,]+\.\d{2})',
            r'Closing Bal[:\s]*([\d,]+\.\d{2})'
        ]
        
        for pattern in closing_patterns:
            closing_match = re.search(pattern, text, re.IGNORECASE)
            if closing_match:
                metadata['closing_balance'] = self._clean_amount(closing_match.group(1))
                break
        
        # Extract currency
        currency_match = re.search(r'Currency[:\s]*([A-Z]{3})', text, re.IGNORECASE)
        if currency_match:
            metadata['currency'] = currency_match.group(1)
        
        # Extract account type
        type_match = re.search(r'Type[:\s]*(\w+)', text, re.IGNORECASE)
        if type_match:
            metadata['account_type'] = type_match.group(1)
        
        return metadata
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names"""
        df.columns = df.columns.str.lower().str.strip()
        
        column_map = {}
        for standard_name, variants in self.COMMON_HEADERS.items():
            for col in df.columns:
                if any(variant in col for variant in variants):
                    column_map[col] = standard_name
                    break
        
        return df.rename(columns=column_map)
    
    def _extract_transactions(self, df: pd.DataFrame) -> List[Dict]:
        """Extract transactions from DataFrame"""
        transactions = []
        
        required_cols = ['date', 'description']
        if not all(col in df.columns for col in required_cols):
            return transactions
        
        for idx, row in df.iterrows():
            try:
                trans_date = self._parse_date(row.get('date'))
                if not trans_date:
                    continue
                
                debit = self._clean_amount(row.get('debit', 0))
                credit = self._clean_amount(row.get('credit', 0))
                balance = self._clean_amount(row.get('balance'))
                
                transaction = {
                    'transaction_date': trans_date.strftime('%Y-%m-%d'),
                    'description': str(row.get('description', '')).strip(),
                    'reference': str(row.get('reference', '')).strip(),
                    'debit_amount': debit,
                    'credit_amount': credit,
                    'balance': balance
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"⚠️ Skipping row {idx}: {str(e)}")
                continue
        
        return transactions
    
    def _extract_metadata(self, df: pd.DataFrame) -> Dict:
        """Extract metadata from DataFrame"""
        metadata = {}
        
        # Extract date range
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'], errors='coerce').dropna()
            if len(dates) > 0:
                metadata['period_start'] = dates.min().strftime('%Y-%m-%d')
                metadata['period_end'] = dates.max().strftime('%Y-%m-%d')
        
        # Extract balances
        if 'balance' in df.columns:
            balances = df['balance'].dropna()
            if len(balances) > 0:
                metadata['opening_balance'] = self._clean_amount(balances.iloc[0])
                metadata['closing_balance'] = self._clean_amount(balances.iloc[-1])
        
        return metadata
    
    def _is_date_string(self, s: str) -> bool:
        """Check if string looks like a date"""
        if not s:
            return False
        
        date_patterns = [
            r'\d{1,2}-[A-Za-z]{3}-\d{2,4}',  # 8-Jan-24
            r'\d{1,2}/[A-Za-z]{3}/\d{2,4}',  # 8/Jan/24
            r'\d{1,2}/\d{1,2}/\d{2,4}',      # 08/01/2024
            r'\d{1,2}-\d{1,2}-\d{2,4}',      # 08-01-2024
            r'\d{4}-\d{2}-\d{2}',            # 2024-01-08
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, str(s), re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def _parse_date(date_str) -> Optional[datetime]:
        """Parse date from various formats"""
        if pd.isna(date_str):
            return None
        
        # Handle Nigerian format: "8-Jan-24"
        date_str = str(date_str).strip()
        
        # Try multiple formats
        date_formats = [
            '%d-%b-%y',    # 8-Jan-24
            '%d-%b-%Y',    # 8-Jan-2024
            '%d/%m/%Y',    # 08/01/2024
            '%d-%m-%Y',    # 08-01-2024
            '%Y-%m-%d',    # 2024-01-08
            '%d %b %Y',    # 8 Jan 2024
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Try pandas
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    
    @staticmethod
    def _clean_amount(amount) -> float:
        """Clean and convert amount to float"""
        if pd.isna(amount):
            return 0.0
        
        amount_str = str(amount).replace('₦', '').replace(',', '').replace(' ', '').strip()
        
        try:
            return float(amount_str)
        except ValueError:
            return 0.0
        
    def _parse_fidelity_pdf_direct(self, file_path: str) -> Dict:
        """Direct parsing for Fidelity Bank PDFs"""
        try:
            from .fidelity_parser import FidelityBankParser
            parser = FidelityBankParser()
            return parser.parse_pdf(file_path)
        except Exception as e:
            logger.error(f"❌ Fidelity direct parser failed: {str(e)}")
            return {'success': False, 'error': str(e)}