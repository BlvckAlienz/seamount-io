# backend/services/bookkeeping/fidelity_parser.py
"""
Direct Fidelity Bank PDF Parser - Hardcoded for your specific PDF format
"""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FidelityBankParser:
    """
    Direct parser for Fidelity Bank PDF statements
    """
    
    def parse_pdf(self, file_path: str) -> Dict:
        """
        Direct parsing of Fidelity Bank PDF with known structure
        """
        try:
            # Extract text using simple method
            text = self._extract_text_simple(file_path)
            
            if not text:
                return {
                    'success': False,
                    'error': 'Could not extract text from PDF'
                }
            
            logger.info(f"🔵 Extracted {len(text)} characters")
            
            # Extract metadata
            metadata = self._extract_metadata(text)
            
            # Extract transactions using direct line-by-line parsing
            transactions = self._extract_transactions_direct(text)
            
            if not transactions:
                # Try alternative extraction
                transactions = self._extract_transactions_alternative(text)
            
            if transactions:
                return {
                    'success': True,
                    'transactions': transactions,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'No transactions found in PDF'
                }
                
        except Exception as e:
            logger.error(f"❌ Fidelity parser error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text_simple(self, file_path: str) -> str:
        """Simple text extraction that preserves whitespace"""
        import PyPDF2
        
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Keep original whitespace
                        text += page_text + "\n"
                
                return text
                
        except Exception as e:
            logger.error(f"❌ Text extraction failed: {str(e)}")
            return ""
    
    def _extract_metadata(self, text: str) -> Dict:
        """Extract metadata from PDF text"""
        metadata = {}
        
        # Extract account number
        acc_patterns = [
            r'Account[:\s]*(\d{8,})',
            r'Account No[:\s]*(\d{8,})',
        ]
        
        for pattern in acc_patterns:
            acc_match = re.search(pattern, text, re.IGNORECASE)
            if acc_match:
                metadata['account_number'] = acc_match.group(1)
                break
        
        # Bank name is Fidelity
        metadata['bank_name'] = 'Fidelity Bank'
        
        # Extract period
        period_match = re.search(r'From\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+to\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})', text, re.IGNORECASE)
        if period_match:
            start_date = self._parse_date(period_match.group(1))
            end_date = self._parse_date(period_match.group(2))
            if start_date:
                metadata['period_start'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                metadata['period_end'] = end_date.strftime('%Y-%m-%d')
        
        # Extract opening balance (look for "Opening Balance" line)
        opening_match = re.search(r'Opening Balance\s+([\d,]+\.\d{2})', text)
        if opening_match:
            metadata['opening_balance'] = self._clean_amount(opening_match.group(1))
        
        # Extract closing balance
        closing_match = re.search(r'Closing Balance\s+([\d,]+\.\d{2})', text)
        if closing_match:
            metadata['closing_balance'] = self._clean_amount(closing_match.group(1))
        
        return metadata
    
    def _extract_transactions_direct(self, text: str) -> List[Dict]:
        """
        Direct extraction for Fidelity Bank table format
        Looking for lines like:
        "8-Jan-24    8-Jan-24    Others    Q3 Visa Card Mtce Fee 2023    50.00    4,950.82"
        """
        transactions = []
        lines = text.split('\n')
        
        # Find where transaction table starts
        start_index = -1
        for i, line in enumerate(lines):
            if 'Opening Balance' in line or 'Transaction Date' in line:
                start_index = i
                break
        
        if start_index == -1:
            # Try to find by date pattern
            for i, line in enumerate(lines):
                if '8-Jan-24' in line or '23-Jan-24' in line:
                    start_index = i
                    break
        
        if start_index == -1:
            return transactions
        
        # Process lines starting from start_index
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            
            # Skip header lines
            if any(word in line.lower() for word in ['transaction date', 'value date', 'channel', 'details', 'opening balance']):
                continue
            
            # Skip empty lines
            if not line or len(line) < 10:
                continue
            
            # Skip page numbers and footers
            if any(word in line.lower() for word in ['page', 'of', 'fidelity bank', 'henry asiegbu']):
                continue
            
            # Try to parse the line
            transaction = self._parse_fidelity_line(line)
            if transaction:
                transactions.append(transaction)
            
            # Also check if this might be a multi-line transaction
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not any(word in next_line.lower() for word in ['jan-24', 'feb-24', 'mar-24', 'apr-24', 'may-24']):
                    # Might be continuation of description
                    if transaction:
                        transaction['description'] += ' ' + next_line
        
        return transactions
    
    def _parse_fidelity_line(self, line: str) -> Optional[Dict]:
        """
        Parse a Fidelity Bank transaction line
        
        Format: Date Date Channel Description Amount Amount
        Example: "8-Jan-24    8-Jan-24    Others    Q3 Visa Card Mtce Fee 2023    50.00    4,950.82"
        """
        try:
            # Split by multiple spaces (2 or more)
            parts = re.split(r'\s{2,}', line.strip())
            
            if len(parts) < 6:
                # Try splitting by any whitespace and reconstruct
                return self._parse_line_fallback(line)
            
            # First two should be dates
            date1 = parts[0]
            date2 = parts[1]
            
            # Parse date
            trans_date = self._parse_date(date1)
            if not trans_date:
                return None
            
            # Last two should be amounts
            amount1_str = parts[-2]
            amount2_str = parts[-1]
            
            # Clean amounts
            amount1 = self._clean_amount(amount1_str)
            amount2 = self._clean_amount(amount2_str)
            
            # Everything between dates and amounts is description
            description_parts = parts[2:-2]
            description = ' '.join(description_parts).strip()
            
            # Determine if debit or credit
            # In Fidelity PDFs, if amount1 > 0 and it's not a balance, it's usually debit for expenses
            line_lower = line.lower()
            
            is_debit = any(word in line_lower for word in [
                'fee', 'charge', 'sms', 'alert', 'levy', 
                'transfer to', 'cob trf to', 'debit', 'withdrawal'
            ])
            
            is_credit = any(word in line_lower for word in [
                'transfer', 'deposit', 'payment', 'received',
                'mega bricks', 'investment', 'ighodalo'
            ]) and 'transfer to' not in line_lower
            
            if is_debit:
                debit = amount1
                credit = 0
            elif is_credit:
                debit = 0
                credit = amount1
            else:
                # Default based on context
                if 'trf to' in description.lower():
                    debit = amount1
                    credit = 0
                else:
                    debit = 0
                    credit = amount1
            
            return {
                'transaction_date': trans_date.strftime('%Y-%m-%d'),
                'description': description,
                'reference': '',
                'debit_amount': debit,
                'credit_amount': credit,
                'balance': amount2
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse line: {line} - Error: {e}")
            return None
    
    def _parse_line_fallback(self, line: str) -> Optional[Dict]:
        """Fallback parsing for lines that don't split cleanly"""
        try:
            # Look for date pattern at start
            date_match = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{2,4})', line)
            if not date_match:
                return None
            
            date_str = date_match.group(1)
            trans_date = self._parse_date(date_str)
            if not trans_date:
                return None
            
            # Find amounts at the end
            amount_pattern = r'([\d,]+\.\d{2})'
            amounts = re.findall(amount_pattern, line)
            
            if len(amounts) < 2:
                return None
            
            amount1 = self._clean_amount(amounts[-2])
            amount2 = self._clean_amount(amounts[-1])
            
            # Extract description (between date and first amount)
            date_end = date_match.end()
            first_amount_start = line.find(amounts[0])
            
            if first_amount_start > date_end:
                description = line[date_end:first_amount_start].strip()
            else:
                # Extract everything that's not date or amounts
                parts = line.split()
                desc_parts = []
                for part in parts:
                    if self._is_date_string(part) or part in amounts:
                        continue
                    desc_parts.append(part)
                description = ' '.join(desc_parts)
            
            # Determine debit/credit
            line_lower = line.lower()
            if any(word in line_lower for word in ['fee', 'charge', 'sms', 'levy', 'trf to']):
                debit = amount1
                credit = 0
            else:
                debit = 0
                credit = amount1
            
            return {
                'transaction_date': trans_date.strftime('%Y-%m-%d'),
                'description': description,
                'reference': '',
                'debit_amount': debit,
                'credit_amount': credit,
                'balance': amount2
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Fallback parsing failed: {e}")
            return None
    
    def _extract_transactions_alternative(self, text: str) -> List[Dict]:
        """Alternative extraction using regex patterns"""
        transactions = []
        
        # Pattern for Fidelity Bank lines
        # Format: Date Date Description Amount Amount
        pattern = r'(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s+(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s+(.*?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
        
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                date1, date2, description, amount1_str, amount2_str = match.groups()
                
                trans_date = self._parse_date(date1)
                if not trans_date:
                    continue
                
                amount1 = self._clean_amount(amount1_str)
                amount2 = self._clean_amount(amount2_str)
                
                # Clean description
                description = description.strip()
                
                # Determine debit/credit
                desc_lower = description.lower()
                if any(word in desc_lower for word in ['fee', 'charge', 'sms', 'levy']):
                    debit = amount1
                    credit = 0
                elif 'transfer to' in desc_lower:
                    debit = amount1
                    credit = 0
                else:
                    debit = 0
                    credit = amount1
                
                transaction = {
                    'transaction_date': trans_date.strftime('%Y-%m-%d'),
                    'description': description,
                    'reference': '',
                    'debit_amount': debit,
                    'credit_amount': credit,
                    'balance': amount2
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"⚠️ Regex match failed: {e}")
                continue
        
        return transactions
    
    def _is_date_string(self, s: str) -> bool:
        """Check if string looks like a date"""
        if not s:
            return False
        
        date_patterns = [
            r'\d{1,2}-[A-Za-z]{3}-\d{2,4}',  # 8-Jan-24
            r'\d{1,2}/[A-Za-z]{3}/\d{2,4}',  # 8/Jan/24
            r'\d{1,2}/\d{1,2}/\d{2,4}',      # 08/01/2024
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, s, re.IGNORECASE):
                return True
        return False
    
    def _parse_date(self, date_str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Handle the case where year is 2423 instead of 2023
        if date_str.endswith('2423') or date_str.endswith('2424'):
            # Fix the year - subtract 400 years
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    day, month, year = parts
                    if year.startswith('24'):  # 2423 or 2424
                        # Convert to proper year (2423 -> 2023, 2424 -> 2024)
                        fixed_year = int(year) - 400
                        date_str = f"{day}-{month}-{fixed_year}"
        
        # Try multiple formats
        date_formats = [
            '%d-%b-%y',    # 8-Jan-24 (THIS IS THE CORRECT FORMAT)
            '%d-%b-%Y',    # 8-Jan-2024
            '%d/%m/%Y',    # 08/01/2024
            '%d-%m-%Y',    # 08-01-2024
            '%Y-%m-%d',    # 2024-01-08
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None
    
    def _clean_amount(self, amount) -> float:
        """Clean and convert amount to float with safety limits"""
        if not amount:
            return 0.0
        
        amount_str = str(amount).replace('₦', '').replace(',', '').replace(' ', '').strip()
        
        try:
            value = float(amount_str)
            
            # Cap at database limit: numeric(15,2) max is 9999999999999.99
            max_value = 9999999999999.99
            if abs(value) > max_value:
                logger.warning(f"⚠️ Amount {value} exceeds max, capping to {max_value}")
                return max_value if value > 0 else -max_value
            
            return value
        except ValueError:
            return 0.0