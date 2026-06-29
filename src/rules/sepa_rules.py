from dataclasses import dataclass
from typing import Callable


# ─── Rule definition ──────────────────────────────────────────────────────────

@dataclass
class ValidationRule:
    field: str            # which key in parsed_fields to check
    description: str      # goes into the finding — human readable
    severity: str         # "ERROR" | "WARNING"
    applies_to: list      # ["SEPA"] | ["MT103"] | ["SEPA", "MT103"]
    country_scope: list   # ["ALL"] | ["GB"] | ["DE"] | ["GB", "DE"]
    check: Callable       # receives parsed_fields dict, returns True (pass) or False (fail)


# ─── Field validators ─────────────────────────────────────────────────────────

def is_valid_iban(value: str) -> bool:
    """
    ISO 13616 IBAN checksum validation.
    Public algorithm — used by all banks implementing SEPA.
    """
    if not value or len(value) < 15:
        return False

    value = value.replace(" ", "").upper()

    # Move first 4 chars to end
    rearranged = value[4:] + value[:4]

    # Convert letters to digits: A=10, B=11 ... Z=35
    digits = ""
    for char in rearranged:
        if char.isalpha():
            digits += str(ord(char) - 55)
        else:
            digits += char

    # Valid IBAN passes mod 97 check
    return int(digits) % 97 == 1


def is_valid_bic(value: str) -> bool:
    """
    BIC must be 8 or 11 characters — public SWIFT specification.
    """
    if not value:
        return False
    return len(value) in (8, 11) and value.isalnum()


def is_valid_amount(value: str) -> bool:
    """
    Amount must be a positive number.
    """
    if not value:
        return False
    try:
        return float(value) > 0
    except ValueError:
        return False


# ─── SEPA rule registry ───────────────────────────────────────────────────────
#
# Source: SEPA Credit Transfer Scheme Rulebook EPC133-08
# Rules are data, not hardcoded if/else — add a new rule by adding one entry.
# country_scope ["ALL"] fires for every payment.
# country_scope ["GB"] fires only when creditor_country == "GB".

SEPA_RULES: list[ValidationRule] = [

    # ── Mandatory fields — ERROR severity ─────────────────────────────────────

    ValidationRule(
        field="creditor_name",
        description="Creditor name is mandatory for all SEPA credit transfers (EPC133-08 AT-21)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: bool(f.get("creditor_name"))
    ),

    ValidationRule(
        field="creditor_iban",
        description="Creditor IBAN is mandatory and must pass ISO 13616 checksum (EPC133-08 AT-20)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: is_valid_iban(f.get("creditor_iban", ""))
    ),

    ValidationRule(
        field="creditor_bic",
        description="Creditor BIC must be a valid 8 or 11 character SWIFT code (EPC133-08 AT-23)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: is_valid_bic(f.get("creditor_bic", ""))
    ),

    ValidationRule(
        field="debtor_name",
        description="Debtor name is mandatory for all SEPA credit transfers (EPC133-08 AT-02)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: bool(f.get("debtor_name"))
    ),

    ValidationRule(
        field="debtor_iban",
        description="Debtor IBAN is mandatory and must pass ISO 13616 checksum (EPC133-08 AT-01)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: is_valid_iban(f.get("debtor_iban", ""))
    ),

    ValidationRule(
        field="amount",
        description="Payment amount is mandatory and must be a positive number (EPC133-08 AT-04)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: is_valid_amount(f.get("amount", ""))
    ),

    ValidationRule(
        field="end_to_end_id",
        description="End-to-end reference is mandatory for payment tracking (EPC133-08 AT-41)",
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: bool(f.get("end_to_end_id"))
    ),

    # ── Country-specific mandatory fields — ERROR severity ────────────────────

    ValidationRule(
        field="ultimate_debtor_name",
        description=(
            "Ultimate Debtor Name is required for GB SEPA payments "
            "per UK SEPA rulebook addendum section 2.9"
        ),
        severity="ERROR",
        applies_to=["SEPA"],
        country_scope=["GB"],
        check=lambda f: bool(f.get("ultimate_debtor_name"))
    ),

    # ── Recommended fields — WARNING severity ─────────────────────────────────

    ValidationRule(
        field="remittance_info",
        description=(
            "Remittance information is absent — creditor bank may reject or "
            "delay the payment without a payment reference (EPC133-08 AT-05)"
        ),
        severity="WARNING",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: bool(f.get("remittance_info"))
    ),

    ValidationRule(
        field="creditor_country",
        description=(
            "Creditor country is absent — required for country-specific "
            "rule scoping and routing decisions"
        ),
        severity="WARNING",
        applies_to=["SEPA"],
        country_scope=["ALL"],
        check=lambda f: bool(f.get("creditor_country"))
    ),
]