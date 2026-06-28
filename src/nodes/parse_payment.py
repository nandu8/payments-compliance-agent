import re
import xml.etree.ElementTree as ET
from typing import Optional

from src.state import PaymentComplianceState

# SEPA pain.001.001.03 namespace
SEPA_NS = {"pain": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_text(element, path: str) -> Optional[str]:
    node = element.find(path, SEPA_NS)
    return node.text.strip() if node is not None and node.text else None


def _find_attr(element, path: str, attr: str) -> Optional[str]:
    node = element.find(path, SEPA_NS)
    return node.get(attr) if node is not None else None


def _parse_error(fmt: str, msg: str) -> dict:
    return {
        "payment_format": fmt,
        "parsed_fields": {},
        "parse_status": "ERROR",
        "parse_error": msg
    }


def _parse_32a(value: str) -> dict:
    """Parse MT103 field 32A — format: YYMMDDCCCAMOUNT e.g. 230615GBP10000,"""
    if value and len(value) >= 9:
        return {
            "value_date": value[:6],
            "currency":   value[6:9],
            "amount":     value[9:].replace(",", ".")
        }
    return {"value_date": None, "currency": None, "amount": None}


# ─── SEPA Parser ──────────────────────────────────────────────────────────────

def _parse_sepa(raw: str) -> dict:
    try:
        root = ET.fromstring(raw)
        tx = root.find(".//pain:CdtTrfTxInf", SEPA_NS)

        if tx is None:
            return _parse_error("SEPA", "Could not locate CdtTrfTxInf transaction block")

        parsed_fields = {
            # Creditor
            "creditor_name":        _find_text(tx, "pain:Cdtr/pain:Nm"),
            "creditor_iban":        _find_text(tx, "pain:CdtrAcct/pain:Id/pain:IBAN"),
            "creditor_bic":         _find_text(tx, "pain:CdtrAgt/pain:FinInstnId/pain:BIC"),
            "creditor_country":     _find_text(tx, "pain:Cdtr/pain:PstlAdr/pain:Ctry"),

            # Debtor
            "debtor_name":          _find_text(tx, "pain:Dbtr/pain:Nm"),
            "debtor_iban":          _find_text(tx, "pain:DbtrAcct/pain:Id/pain:IBAN"),

            # Ultimate debtor — optional in spec, required for GB per rulebook addendum
            "ultimate_debtor_name": _find_text(tx, "pain:UltmtDbtr/pain:Nm"),

            # Payment details
            "amount":               _find_text(tx, "pain:Amt/pain:InstdAmt"),
            "currency":             _find_attr(tx, "pain:Amt/pain:InstdAmt", "Ccy"),
            "end_to_end_id":        _find_text(tx, "pain:PmtId/pain:EndToEndId"),
            "remittance_info":      _find_text(tx, "pain:RmtInf/pain:Ustrd"),
            "purpose_code":         _find_text(tx, "pain:Purp/pain:Cd"),
        }

        return {
            "payment_format": "SEPA",
            "parsed_fields":  parsed_fields,
            "parse_status":   "SUCCESS",
            "parse_error":    None
        }

    except ET.ParseError as e:
        return _parse_error("SEPA", f"XML parse failed: {e}")


# ─── MT103 Parser ─────────────────────────────────────────────────────────────

def _parse_mt103(raw: str) -> dict:
    try:
        fields = {}
        blocks = re.split(r'(?=:\d{2}[A-Z]?:)', raw)

        for block in blocks:
            match = re.match(r':(\d{2}[A-Z]?):(.*)', block, re.DOTALL)
            if match:
                fields[match.group(1)] = match.group(2).strip()

        parsed_fields = {
            "transaction_reference": fields.get("20"),
            "ordering_customer":     fields.get("50K") or fields.get("50A"),
            "beneficiary_customer":  fields.get("59")  or fields.get("59A"),
            "remittance_info":       fields.get("70"),
            "details_of_charges":    fields.get("71A"),   # OUR / BEN / SHA
            "sender_to_receiver":    fields.get("72"),
            **_parse_32a(fields.get("32A", "")),
        }

        return {
            "payment_format": "MT103",
            "parsed_fields":  parsed_fields,
            "parse_status":   "SUCCESS",
            "parse_error":    None
        }

    except Exception as e:
        return _parse_error("MT103", f"MT103 parse failed: {e}")


# ─── Node function ────────────────────────────────────────────────────────────

def parse_payment(state: PaymentComplianceState) -> dict:
    raw = state["raw_payment"].strip()

    if raw.startswith("<"):
        return _parse_sepa(raw)
    elif raw.startswith(":20:") or raw.startswith("{1:"):
        return _parse_mt103(raw)
    else:
        return _parse_error(
            "UNKNOWN",
            "Unrecognised message format — expected SEPA XML or MT103"
        )


# ─── Conditional edge ────────────────────────────────────────────────────────

def route_after_parse(state: PaymentComplianceState) -> str:
    if state["parse_status"] == "ERROR":
        return "generate_audit_report"
    return "validate_fields"