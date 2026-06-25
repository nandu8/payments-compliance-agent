from typing import Optional
from typing_extensions import TypedDict


class ValidationFinding(TypedDict):
    field: str
    issue: str
    severity: str        # "ERROR" | "WARNING"


class RegulationClause(TypedDict):
    field: str
    query: str
    clause: str          # retrieved text from RAG
    source: str          # e.g. "SEPA EPC133-08 section 2.19"


class PaymentComplianceState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    raw_payment: str
    payment_format: Optional[str]     # "SEPA" | "MT103" | "UNKNOWN"

    # ── After parse_payment ────────────────────────────────
    parsed_fields: Optional[dict]
    parse_status: Optional[str]       # "SUCCESS" | "ERROR"
    parse_error: Optional[str]

    # ── After validate_fields ──────────────────────────────
    validation_findings: Optional[list[ValidationFinding]]
    validation_status: Optional[str]  # "PASS" | "FAIL" | "AMBIGUOUS"

    # ── After retrieve_context ─────────────────────────────
    regulation_context: Optional[list[RegulationClause]]

    # ── After human_review ────────────────────────────────
    human_decision: Optional[str]     # "APPROVE" | "REJECT"
    human_notes: Optional[str]

    # ── Final output ───────────────────────────────────────
    audit_report: Optional[str]
    final_verdict: Optional[str]      # "APPROVED" | "REJECTED" | "HUMAN_APPROVED" | "HUMAN_REJECTED"