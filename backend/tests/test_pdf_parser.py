# test_pdf_parser.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.bookkeeping.parser_service import BankStatementParser

parser = BankStatementParser()
result = parser.parse_file("path/to/your/Account_Statement_7819.pdf", "pdf")

print(f"Success: {result.get('success')}")
print(f"Transaction count: {len(result.get('transactions', []))}")
print(f"Error: {result.get('error', 'None')}")

if result.get('transactions'):
    print("\nFirst 5 transactions:")
    for i, tx in enumerate(result['transactions'][:5]):
        print(f"{i+1}. {tx['transaction_date']} - {tx['description'][:50]}... - Debit: {tx['debit_amount']}, Credit: {tx['credit_amount']}")