import pytest
from pathlib import Path
from src.nodes.parse_payment import parse_payment, route_after_parse

FIXTURES = Path(__file__).parent / "fixtures"


def _load(filename: str) -> str:
    return (FIXTURES / filename).read_text()


# ─── SEPA tests ───────────────────────────────────────────────────────────────

def test_sepa_valid_parses_successfully():
    state = {"raw_payment": _load("sepa_valid.xml")}
    result = parse_payment(state)

    assert result["parse_status"] == "SUCCESS"
    assert result["payment_format"] == "SEPA"
    assert result["parsed_fields"]["creditor_name"] == "John Smith"
    assert result["parsed_fields"]["creditor_iban"] == "GB94BARC20201530093459"
    assert result["parsed_fields"]["creditor_country"] == "GB"
    assert result["parsed_fields"]["ultimate_debtor_name"] == "ACME Corporation Ltd"
    assert result["parsed_fields"]["currency"] == "GBP"
    assert result["parse_error"] is None


def test_sepa_missing_fields_still_parses():
    # Parser should succeed even when fields are missing
    # Validation catches the missing fields — not the parser
    state = {"raw_payment": _load("sepa_missing_fields.xml")}
    result = parse_payment(state)

    assert result["parse_status"] == "SUCCESS"
    assert result["parsed_fields"]["creditor_name"] is None
    assert result["parsed_fields"]["ultimate_debtor_name"] is None


def test_sepa_malformed_xml_returns_error():
    state = {"raw_payment": "<Document><broken"}
    result = parse_payment(state)

    assert result["parse_status"] == "ERROR"
    assert "XML parse failed" in result["parse_error"]


# ─── MT103 tests ──────────────────────────────────────────────────────────────

def test_mt103_valid_parses_successfully():
    state = {"raw_payment": _load("mt103_valid.txt")}
    result = parse_payment(state)

    assert result["parse_status"] == "SUCCESS"
    assert result["payment_format"] == "MT103"
    assert result["parsed_fields"]["transaction_reference"] == "REF123456789"
    assert result["parsed_fields"]["currency"] == "GBP"
    assert result["parsed_fields"]["amount"] == "10000.00"
    assert result["parsed_fields"]["details_of_charges"] == "SHA"


# ─── Unknown format test ───────────────────────────────────────────────────────

def test_unknown_format_returns_error():
    state = {"raw_payment": "RANDOM GARBAGE INPUT"}
    result = parse_payment(state)

    assert result["parse_status"] == "ERROR"
    assert result["payment_format"] == "UNKNOWN"


# ─── Routing tests ────────────────────────────────────────────────────────────

def test_route_after_parse_success_goes_to_validate():
    state = {"parse_status": "SUCCESS"}
    assert route_after_parse(state) == "validate_fields"


def test_route_after_parse_error_goes_to_report():
    state = {"parse_status": "ERROR"}
    assert route_after_parse(state) == "generate_audit_report"