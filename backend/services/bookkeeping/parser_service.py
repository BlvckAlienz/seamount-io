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

logger = logging.getLogger(__name__)

class BankStatementParser:
    """
    Parse bank statements from multiple formats (CSV, Excel, PDF)
    """
    
    # Common Nigerian bank statement headers (flexible matching)
    COMMON_HEADERS = {
        'date': ['date', 'transaction date', 'trans date', 'posting date', 'value date'],
        'description': ['description', 'narration', 'details', 'transaction details', 'particulars'],
        'debit': ['debit', 'debit amount', 'withdrawal', 'dr', 'debits'],
        'credit': ['credit', 'credit amount', 'deposit', 'cr', 'credits'],
        'balance': ['balance', 'running balance', 'closing balance', 'book balance'],
        'reference': ['reference', 'ref', 'transaction ref', 'ref no']
    }
    
    def __init__(self):
        self.supported_formats = ['csv', 'xlsx', 'xls', 'pdf']
    
    def parse_file(self, file_path: str, file_type: str) -> Dict:
        """
        Main entry point - parse any supported file type
        
        Returns:
            {
                'success': bool,
                'transactions': List[Dict],
                'metadata': Dict,
                'error': Optional[str]
            }
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
            # Try multiple encodings (Nigerian banks use different formats)
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
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Extract transactions
            transactions = self._extract_transactions(df)
            
            # Extract metadata
            metadata = self._extract_metadata(df)
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ CSV parsing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_excel(self, file_path: str) -> Dict:
        """Parse Excel bank statement"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Extract transactions
            transactions = self._extract_transactions(df)
            
            # Extract metadata
            metadata = self._extract_metadata(df)
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Excel parsing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_pdf_with_pdfplumber(self, file_path: str) -> Dict:
        """
        Parse PDF using pdfplumber (better for tables)
        """
        try:
            transactions = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables
                    tables = page.extract_tables()
                    
                    logger.info(f"🔵 Page {page_num + 1}: Found {len(tables)} tables")
                    
                    for table in tables:
                        logger.info(f"🔵 Table has {len(table)} rows")
                        
                        # Skip header rows (usually first 2-3 rows)
                        for row in table[2:]:
                            if len(row) >= 5:
                                try:
                                    date_str = row[0]
                                    desc = row[1]
                                    debit = row[2] or '0'
                                    credit = row[3] or '0'
                                    balance = row[4] or '0'
                                    
                                    trans_date = self._parse_date(date_str)
                                    
                                    if trans_date:
                                        transaction = {
                                            'transaction_date': trans_date.strftime('%Y-%m-%d'),
                                            'description': desc.strip() if desc else '',
                                            'reference': '',
                                            'debit_amount': self._clean_amount(debit),
                                            'credit_amount': self._clean_amount(credit),
                                            'balance': self._clean_amount(balance)
                                        }
                                        transactions.append(transaction)
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to parse row: {e}")
                                    continue
            
            logger.info(f"✅ pdfplumber extracted {len(transactions)} transactions")
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': {}
            }
        
        except Exception as e:
            logger.error(f"❌ pdfplumber parsing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_pdf(self, file_path: str) -> Dict:
        """
        Parse PDF bank statement
        """
        # Try pdfplumber first (better for tables)
        try:
            result = self._parse_pdf_with_pdfplumber(file_path)
            if result['success'] and len(result.get('transactions', [])) > 0:
                logger.info("✅ pdfplumber parsing successful")
                return result
        except Exception as e:
            logger.warning(f"⚠️ pdfplumber failed, trying PyPDF2: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            
            # 🔵 LOG EXTRACTED TEXT
            logger.info(f"🔵 PDF TEXT LENGTH: {len(text)} characters")
            logger.info(f"🔵 PDF TEXT PREVIEW (first 500 chars):")
            logger.info(text[:500])
            logger.info(f"🔵 PDF TEXT PREVIEW (last 500 chars):")
            logger.info(text[-500:])
            
            # Extract transactions using regex patterns
            transactions = self._extract_from_text(text)
            
            # Extract metadata
            metadata = self._extract_metadata_from_text(text)
            
            return {
                'success': True,
                'transactions': transactions,
                'metadata': metadata,
                'warning': 'PDF parsing is experimental. Verify accuracy.'
            }
            
        except Exception as e:
            logger.error(f"❌ PDF parsing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to standard format
        """
        # Convert to lowercase and strip whitespace
        df.columns = df.columns.str.lower().str.strip()
        
        # Map to standard names
        column_map = {}
        for standard_name, variants in self.COMMON_HEADERS.items():
            for col in df.columns:
                if any(variant in col for variant in variants):
                    column_map[col] = standard_name
                    break
        
        df = df.rename(columns=column_map)
        
        logger.info(f"✅ Normalized columns: {list(df.columns)}")
        return df
    
    def _extract_transactions(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extract transactions from normalized DataFrame
        """
        transactions = []
        
        # Ensure required columns exist
        required_cols = ['date', 'description']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns. Found: {list(df.columns)}")
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                trans_date = self._parse_date(row.get('date'))
                
                if not trans_date:
                    continue  # Skip invalid rows
                
                # Extract amounts
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
        
        logger.info(f"✅ Extracted {len(transactions)} transactions")
        return transactions
    
    def _extract_metadata(self, df: pd.DataFrame) -> Dict:
        """Extract metadata from statement"""
        try:
            # Try to extract bank name, account number, period
            metadata = {}
            
            # Account number (look in first few rows)
            for idx in range(min(10, len(df))):
                row_text = ' '.join(str(v) for v in df.iloc[idx].values)
                acc_match = re.search(r'\b\d{10,}\b', row_text)
                if acc_match:
                    metadata['account_number'] = acc_match.group()
                    break
            
            # Date range
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date'], errors='coerce').dropna()
                if len(dates) > 0:
                    metadata['period_start'] = dates.min().strftime('%Y-%m-%d')
                    metadata['period_end'] = dates.max().strftime('%Y-%m-%d')
            
            # Balances
            if 'balance' in df.columns:
                balances = df['balance'].dropna()
                if len(balances) > 0:
                    metadata['opening_balance'] = self._clean_amount(balances.iloc[0])
                    metadata['closing_balance'] = self._clean_amount(balances.iloc[-1])
            
            return metadata
            
        except Exception as e:
            logger.warning(f"⚠️ Metadata extraction failed: {str(e)}")
            return {}
    
    def _extract_from_text(self, text: str) -> List[Dict]:
        """
        Extract transactions from PDF text (regex-based)
        Supports multiple Nigerian bank formats
        """
        transactions = []
        
        logger.info(f"🔵 Attempting to extract transactions from text...")
        
        # Pattern 1: Date | Description | Debit | Credit | Balance
        pattern1 = r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.{10,}?)\s+([\d,]+\.?\d{2})\s+([\d,]+\.?\d{2})\s+([\d,]+\.?\d{2})'
        
        # Pattern 2: Date | Description | Amount | Balance (with Dr/Cr indicator)
        pattern2 = r'(\d{2}[/-]\d{2}[/-]\d{4})\s+(.{10,}?)\s+([\d,]+\.?\d{2})\s+(Dr|Cr)\s+([\d,]+\.?\d{2})'
        
        # Pattern 3: Date Description Amount Type Balance (space-separated)
        pattern3 = r'(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})\s+(.{10,}?)\s+([\d,]+\.?\d{2})\s+([\d,]+\.?\d{2})'
        
        # Try each pattern
        for pattern_num, pattern in enumerate([pattern1, pattern2, pattern3], 1):
            logger.info(f"🔵 Trying pattern {pattern_num}...")
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            logger.info(f"🔵 Pattern {pattern_num} found {len(matches)} matches")
            
            if matches:
                for match in matches:
                    try:
                        groups = match.groups()
                        logger.info(f"🔵 Match groups: {groups}")
                        
                        # Parse based on pattern
                        if pattern_num == 1:
                            date_str, desc, debit, credit, balance = groups
                            trans_date = self._parse_date(date_str)
                            
                            if trans_date:
                                transaction = {
                                    'transaction_date': trans_date.strftime('%Y-%m-%d'),
                                    'description': desc.strip(),
                                    'reference': '',
                                    'debit_amount': self._clean_amount(debit),
                                    'credit_amount': self._clean_amount(credit),
                                    'balance': self._clean_amount(balance)
                                }
                                transactions.append(transaction)
                        
                        elif pattern_num == 2:
                            date_str, desc, amount, dr_cr, balance = groups
                            trans_date = self._parse_date(date_str)
                            
                            if trans_date:
                                amt = self._clean_amount(amount)
                                transaction = {
                                    'transaction_date': trans_date.strftime('%Y-%m-%d'),
                                    'description': desc.strip(),
                                    'reference': '',
                                    'debit_amount': amt if dr_cr == 'Dr' else 0,
                                    'credit_amount': amt if dr_cr == 'Cr' else 0,
                                    'balance': self._clean_amount(balance)
                                }
                                transactions.append(transaction)
                        
                        elif pattern_num == 3:
                            date_str, desc, debit, credit = groups
                            trans_date = self._parse_date(date_str)
                            
                            if trans_date:
                                transaction = {
                                    'transaction_date': trans_date.strftime('%Y-%m-%d'),
                                    'description': desc.strip(),
                                    'reference': '',
                                    'debit_amount': self._clean_amount(debit),
                                    'credit_amount': self._clean_amount(credit),
                                    'balance': 0
                                }
                                transactions.append(transaction)
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse match: {str(e)}")
                        continue
                
                # If we found transactions, stop trying patterns
                if transactions:
                    logger.info(f"✅ Pattern {pattern_num} successfully extracted {len(transactions)} transactions")
                    break
        
        if not transactions:
            logger.warning(f"⚠️ No transactions extracted from PDF")
            logger.warning(f"⚠️ Text sample: {text[:200]}")
        
        logger.info(f"✅ Extracted {len(transactions)} transactions from PDF")
        return transactions
    
    def _extract_metadata_from_text(self, text: str) -> Dict:
        """Extract metadata from PDF text"""
        metadata = {}
        
        # Extract account number
        acc_match = re.search(r'Account\s*Number[:\s]+(\d{10,})', text, re.IGNORECASE)
        if acc_match:
            metadata['account_number'] = acc_match.group(1)
        
        # Extract bank name
        banks = ['GTBank', 'Access', 'Zenith', 'First Bank', 'UBA', 'Stanbic', 'Fidelity']
        for bank in banks:
            if bank.lower() in text.lower():
                metadata['bank_name'] = bank
                break
        
        return metadata
    
    @staticmethod
    def _parse_date(date_str) -> Optional[datetime]:
        """Parse date from various formats"""
        if pd.isna(date_str):
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%m/%d/%Y',
            '%d %b %Y',
            '%d-%b-%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except:
                continue
        
        # Try pandas parsing as last resort
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    
    @staticmethod
    def _clean_amount(amount) -> float:
        """Clean and convert amount to float"""
        if pd.isna(amount):
            return 0.0
        
        # Remove currency symbols, commas, spaces
        amount_str = str(amount).replace('₦', '').replace(',', '').strip()
        
        try:
            return float(amount_str)
        except ValueError:
            return 0.0