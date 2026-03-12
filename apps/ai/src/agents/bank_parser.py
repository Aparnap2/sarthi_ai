"""
BankStatementParser — OSS only, zero cost.
Supports: HDFC, ICICI, SBI, Axis, Kotak (CSV/Excel).
Fallback: pdfplumber for PDF statements.
"""
import pandas as pd
import pdfplumber
from pathlib import Path
from datetime import datetime
from typing import Optional

BANK_SIGNATURES = {
    "HDFC": ["Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt (INR)", "Deposit Amt (INR)"],
    "ICICI": ["Transaction Date", "Transaction Remarks", "Withdrawal Amount (INR)", "Deposit Amount (INR)"],
    "SBI": ["Txn Date", "Description", "Ref No./Cheque No.", "Debit", "Credit"],
    "AXIS": ["Tran Date", "CHQNO", "PARTICULARS", "WITHDRAWAL", "DEPOSIT"],
    "KOTAK": ["Txn Date", "Description", "Ref No", "Debit Amount", "Credit Amount"],
}

COLUMN_MAP = {
    "HDFC": {"date": "Date", "description": "Narration", "debit": "Withdrawal Amt (INR)", "credit": "Deposit Amt (INR)", "balance": "Closing Balance (INR)"},
    "ICICI": {"date": "Transaction Date", "description": "Transaction Remarks", "debit": "Withdrawal Amount (INR)", "credit": "Deposit Amount (INR)", "balance": "Balance (INR)"},
    "SBI": {"date": "Txn Date", "description": "Description", "debit": "Debit", "credit": "Credit", "balance": "Balance"},
}

class BankStatementParser:
    def parse(self, filepath: str) -> list[dict]:
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix in [".csv"]:
            return self._parse_csv(filepath)
        elif suffix in [".xlsx", ".xls"]:
            return self._parse_excel(filepath)
        elif suffix == ".pdf":
            return self._parse_pdf(filepath)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def _detect_bank(self, columns: list[str]) -> str:
        for bank, sig_cols in BANK_SIGNATURES.items():
            if any(col in columns for col in sig_cols[:2]):
                return bank
        return "UNKNOWN"

    def _parse_csv(self, filepath: str) -> list[dict]:
        df = pd.read_csv(filepath, skiprows=0)
        df.columns = df.columns.str.strip()
        bank = self._detect_bank(list(df.columns))
        return self._normalize(df, bank)

    def _parse_excel(self, filepath: str) -> list[dict]:
        df = pd.read_excel(filepath)
        df.columns = df.columns.str.strip()
        bank = self._detect_bank(list(df.columns))
        return self._normalize(df, bank)

    def _normalize(self, df: pd.DataFrame, bank: str) -> list[dict]:
        col_map = COLUMN_MAP.get(bank, {})
        if not col_map:
            raise ValueError(f"No column map for bank: {bank}")

        transactions = []
        for _, row in df.iterrows():
            try:
                raw_date = str(row.get(col_map["date"], "")).strip()
                date = self._parse_date(raw_date)
                if not date:
                    continue

                debit_raw = str(row.get(col_map["debit"], "0")).replace(",", "")
                credit_raw = str(row.get(col_map["credit"], "0")).replace(",", "")
                balance_raw = str(row.get(col_map.get("balance", ""), "0")).replace(",", "")

                debit = float(debit_raw) if debit_raw.replace(".","").isdigit() else 0.0
                credit = float(credit_raw) if credit_raw.replace(".","").isdigit() else 0.0
                balance = float(balance_raw) if balance_raw.replace(".","").isdigit() else None

                transactions.append({
                    "date": date,
                    "description": str(row.get(col_map["description"], "")).strip(),
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "bank_name": bank,
                    "category": None,
                    "raw_source": "csv"
                })
            except Exception:
                continue

        return transactions

    def _parse_date(self, raw: str) -> str | None:
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%b-%Y", "%d %b %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _parse_pdf(self, filepath: str) -> list[dict]:
        transactions = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    headers = [str(h).strip() for h in table[0]]
                    bank = self._detect_bank(headers)
                    if bank == "UNKNOWN":
                        continue
                    df = pd.DataFrame(table[1:], columns=headers)
                    transactions.extend(self._normalize(df, bank))
        return transactions

    def categorize_transactions(self, transactions: list[dict]) -> list[dict]:
        """Use LLM to auto-categorize transactions."""
        from src.config.llm import get_llm_client
        client = get_llm_client()
        
        prompt = f"""Categorize these bank transactions.
Categories: Revenue | Payroll | Infrastructure | Food/Meals | Bank Charges | Tax | Vendor Payment | Transfer | Interest | Uncategorized

Transactions: {transactions}

Return JSON array: [{{"description": str, "category": str}}]"""

        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        categories = result if isinstance(result, list) else result.get("transactions", [])
        
        for txn, cat in zip(transactions, categories):
            txn["category"] = cat.get("category", "Uncategorized")
        
        return transactions
