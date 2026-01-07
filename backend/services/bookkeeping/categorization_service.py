# backend/services/bookkeeping/categorization_service.py
"""
AI-Powered Transaction Categorization using Groq (FREE) or Claude
"""

import re
import logging
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class TransactionCategorizer:
    """
    Categorize transactions using Groq (FREE) or Claude API + rule-based fallback
    """
    
    def __init__(self, groq_api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        """
        Initialize categorizer with Groq (preferred) or Claude API
        
        Priority: Groq (free) > Claude (paid) > Rules (fallback)
        """
        self.groq_client = None
        self.anthropic_client = None
        
        # Try Groq first (FREE)
        if groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_api_key)
                logger.info("✅ Groq AI initialized (FREE)")
            except ImportError:
                logger.warning("⚠️ Groq not installed. Run: pip install groq")
            except Exception as e:
                logger.warning(f"⚠️ Groq initialization failed: {e}")
        
        # Fallback to Claude if available
        if not self.groq_client and anthropic_api_key:
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=anthropic_api_key)
                logger.info("✅ Claude AI initialized")
            except Exception as e:
                logger.warning(f"⚠️ Claude initialization failed: {e}")
        
        # Fallback: Keyword-based rules
        self.keyword_rules = {
            '4000': {  # Sales Revenue
                'keywords': ['transfer in', 'payment received', 'deposit', 'credit alert', 'payment from'],
                'category': 'Sales Revenue'
            },
            '5000': {  # COGS
                'keywords': ['purchase', 'supplier', 'inventory', 'stock'],
                'category': 'Cost of Goods Sold'
            },
            '6000': {  # Salaries
                'keywords': ['salary', 'wages', 'payroll', 'staff', 'employee'],
                'category': 'Salaries & Wages'
            },
            '6100': {  # Rent
                'keywords': ['rent', 'lease'],
                'category': 'Rent Expense'
            },
            '6200': {  # Utilities
                'keywords': ['electricity', 'water', 'internet', 'dstv', 'gotv', 'nepa', 'phcn'],
                'category': 'Utilities'
            },
            '6400': {  # Marketing
                'keywords': ['advertising', 'marketing', 'promo', 'facebook ads', 'google ads'],
                'category': 'Marketing & Advertising'
            },
            '6800': {  # Bank Charges
                'keywords': ['bank charge', 'sms charge', 'vat', 'stamp duty', 'commission'],
                'category': 'Bank Charges'
            },
            '1000': {  # Cash at Bank
                'keywords': ['atm withdrawal', 'cash', 'pos'],
                'category': 'Cash Withdrawal'
            }
        }
    
    async def categorize_batch(
        self,
        transactions: List[Dict],
        use_ai: bool = True
    ) -> List[Dict]:
        """
        Categorize a batch of transactions
        
        Args:
            transactions: List of transaction dicts
            use_ai: Whether to use Groq/Claude AI (True) or rule-based (False)
        
        Returns:
            Transactions with categorization added
        """
        if use_ai and (self.groq_client or self.anthropic_client):
            return await self._categorize_with_ai(transactions)
        else:
            return self._categorize_with_rules(transactions)
    
    async def _categorize_with_ai(self, transactions: List[Dict]) -> List[Dict]:
        """
        Use Groq (preferred) or Claude to categorize transactions
        
        Strategy:
        1. Send batch of transactions to AI
        2. Ask AI to categorize based on Nigerian accounting standards
        3. Parse AI's response into structured format
        """
        try:
            # Prepare transactions for AI
            trans_list = []
            for idx, trans in enumerate(transactions):
                trans_list.append(
                    f"{idx+1}. Date: {trans['transaction_date']}, "
                    f"Description: {trans['description']}, "
                    f"Debit: ₦{trans['debit_amount']:,.2f}, "
                    f"Credit: ₦{trans['credit_amount']:,.2f}"
                )
            
            trans_text = '\n'.join(trans_list)
            
            # AI prompt
            prompt = f"""You are an expert Nigerian accountant. Categorize these bank transactions into the appropriate chart of accounts.

Available accounts:
- 1000: Cash at Bank
- 4000: Sales Revenue
- 4100: Service Revenue
- 5000: Cost of Goods Sold
- 6000: Salaries & Wages
- 6100: Rent Expense
- 6200: Utilities
- 6300: Office Supplies
- 6400: Marketing & Advertising
- 6500: Professional Fees
- 6600: Insurance
- 6800: Bank Charges
- 6900: Miscellaneous Expenses
- 7100: VAT Expense

Transactions:
{trans_text}

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
  "categorizations": [
    {{
      "index": 1,
      "account_code": "6000",
      "category": "Salaries & Wages",
      "confidence": 0.95
    }}
  ]
}}

Rules:
- Debits (withdrawals) are usually expenses
- Credits (deposits) are usually revenue
- Be specific with categories
- Confidence: 0.0-1.0"""

            response_text = None
            
            # Try Groq first (FREE & FAST)
            if self.groq_client:
                try:
                    completion = self.groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",  # Fast & accurate
                        messages=[
                            {"role": "system", "content": "You are an expert Nigerian accountant. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    response_text = completion.choices[0].message.content
                    logger.info(f"✅ Groq categorized {len(transactions)} transactions")
                    
                except Exception as groq_error:
                    logger.error(f"❌ Groq failed: {groq_error}")
                    # Fall through to Claude
            
            # Fallback to Claude if Groq failed
            if not response_text and self.anthropic_client:
                try:
                    message = self.anthropic_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4000,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    response_text = message.content[0].text
                    logger.info(f"✅ Claude categorized {len(transactions)} transactions")
                    
                except Exception as claude_error:
                    logger.error(f"❌ Claude failed: {claude_error}")
            
            if not response_text:
                raise Exception("Both Groq and Claude failed")
            
            # Parse AI's JSON response
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)
            
            response_json = json.loads(response_text)
            categorizations = response_json.get('categorizations', [])
            
            # Apply categorizations to transactions
            for cat in categorizations:
                idx = cat['index'] - 1  # Convert to 0-based index
                if 0 <= idx < len(transactions):
                    transactions[idx]['account_code'] = cat['account_code']
                    transactions[idx]['category'] = cat['category']
                    transactions[idx]['confidence_score'] = cat['confidence']
                    transactions[idx]['is_manually_categorized'] = False
            
            return transactions
            
        except Exception as e:
            logger.error(f"❌ AI categorization failed: {str(e)}")
            logger.info("⚠️ Falling back to rule-based categorization")
            return self._categorize_with_rules(transactions)
    
    def _categorize_with_rules(self, transactions: List[Dict]) -> List[Dict]:
        """
        Fallback: Rule-based categorization using keywords
        """
        for trans in transactions:
            desc_lower = trans['description'].lower()
            
            # Check each rule
            matched = False
            for account_code, rule in self.keyword_rules.items():
                if any(keyword in desc_lower for keyword in rule['keywords']):
                    trans['account_code'] = account_code
                    trans['category'] = rule['category']
                    trans['confidence_score'] = 0.80  # Rule-based = high confidence
                    trans['is_manually_categorized'] = False
                    matched = True
                    break
            
            # Default: Miscellaneous
            if not matched:
                if trans['debit_amount'] > 0:
                    trans['account_code'] = '6900'
                    trans['category'] = 'Miscellaneous Expenses'
                else:
                    trans['account_code'] = '4300'
                    trans['category'] = 'Other Income'
                trans['confidence_score'] = 0.50  # Low confidence
                trans['is_manually_categorized'] = False
        
        logger.info(f"✅ Rule-based categorization complete")
        return transactions
    
    def learn_from_manual_categorization(
        self,
        description: str,
        account_code: str,
        category: str
    ) -> Dict:
        """
        Create a new rule from user's manual categorization
        This will be stored in categorization_rules table
        """
        # Extract keywords from description
        keywords = self._extract_keywords(description)
        
        return {
            'keyword_pattern': ' OR '.join(keywords),
            'account_code': account_code,
            'category': category,
            'rule_type': 'learned',
            'priority': 10  # User rules have high priority
        }
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract meaningful keywords from transaction description"""
        # Remove common words
        stop_words = {'the', 'and', 'or', 'for', 'to', 'from', 'at', 'by', 'of'}
        
        # Split and filter
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:3]  # Return top 3 keywords