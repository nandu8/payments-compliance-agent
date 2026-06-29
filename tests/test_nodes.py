import pytest
from pathlib import Path
from src.nodes.parse_payment import parse_payment, route_after_parse
from src.rules.sepa_rules import SEPA_RULES, is_valid_iban, is_valid_bic, is_valid_amount
from src.nodes.validate_fields import validate_fields
from src.nodes.retrieve_context import retrieve_context, route_after_retrieve

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


# ─── Validator unit tests ─────────────────────────────────────────────────────

def test_valid_iban_passes():
    assert is_valid_iban("GB29NWBK60161331926819") is True

def test_invalid_iban_fails():
    assert is_valid_iban("GB00NWBK60161331926819") is False

def test_empty_iban_fails():
    assert is_valid_iban("") is False

def test_valid_bic_8_chars_passes():
    assert is_valid_bic("NWBKGB2L") is True

def test_valid_bic_11_chars_passes():
    assert is_valid_bic("NWBKGB2LXXX") is True

def test_invalid_bic_fails():
    assert is_valid_bic("INVALID") is False

def test_valid_amount_passes():
    assert is_valid_amount("10000.00") is True

def test_zero_amount_fails():
    assert is_valid_amount("0") is False

def test_negative_amount_fails():
    assert is_valid_amount("-100") is False


# ─── Rule registry tests ──────────────────────────────────────────────────────

def test_gb_rule_exists_in_registry():
    gb_rules = [r for r in SEPA_RULES if "GB" in r.country_scope]
    assert len(gb_rules) > 0

def test_all_rules_have_valid_severity():
    for rule in SEPA_RULES:
        assert rule.severity in ("ERROR", "WARNING"), \
            f"Rule {rule.field} has invalid severity: {rule.severity}"

def test_all_rules_have_check_callable():
    for rule in SEPA_RULES:
        assert callable(rule.check), \
            f"Rule {rule.field} has no callable check"

def test_creditor_name_rule_fails_on_empty():
    rule = next(r for r in SEPA_RULES if r.field == "creditor_name")
    assert rule.check({"creditor_name": None}) is False
    assert rule.check({"creditor_name": "John Smith"}) is True

def test_gb_ultimate_debtor_rule_fails_when_absent():
    rule = next(r for r in SEPA_RULES if r.field == "ultimate_debtor_name")
    assert rule.check({"ultimate_debtor_name": None}) is False
    assert rule.check({"ultimate_debtor_name": "ACME Ltd"}) is True

# Validate fields tests

def test_valid_sepa_passes():
    state = {
        "payment_format": "SEPA",
        "parsed_fields": {
            "creditor_name": "John Smith",
            "creditor_iban": "GB29NWBK60161331926819",
            "creditor_bic": "BARCGB22",
            "debtor_name": "ACME Corp",
            "debtor_iban": "GB29NWBK60161331926819",
            "amount": "10000.00",
            "end_to_end_id": "E2E001",
            "ultimate_debtor_name": "ACME Corp Ltd",
            "remittance_info": "Invoice INV-001",
            "creditor_country": "GB"
        }
    }
    result = validate_fields(state)
    print(f"{result['validation_findings']}")
    assert result["validation_status"] == "PASS"
    assert len(result["validation_findings"]) == 0
    print(f"{result['validation_findings']}")

def test_missing_creditor_name_returns_fail():
    state = {
        "payment_format": "SEPA",
        "parsed_fields": {
            "creditor_iban": "GB29NWBK60161331926819",
            "creditor_bic": "BARCGB22",
            "debtor_name": "ACME Corp",
            "debtor_iban": "GB29NWBK60161331926819",
            "amount": "10000.00",
            "end_to_end_id": "E2E001",
            "ultimate_debtor_name": "ACME Corp Ltd",
            "remittance_info": "Invoice INV-001",
            "creditor_country": "GB"
        }
    }
    result = validate_fields(state)
    assert result["validation_status"] == "FAIL"
    assert len(result["validation_findings"]) == 1

def test_missing_ultmate_debtor_name_returns_fail():
    state = {
        "payment_format": "SEPA",
        "parsed_fields": {
            "creditor_name": "John Smith",
            "creditor_iban": "GB29NWBK60161331926819",
            "creditor_bic": "BARCGB22",
            "debtor_name": "ACME Corp",
            "debtor_iban": "GB29NWBK60161331926819",
            "amount": "10000.00",
            "end_to_end_id": "E2E001",
            "remittance_info": "Invoice INV-001",
            "creditor_country": "GB"
        }
    }
    result = validate_fields(state)
    assert result["validation_status"] == "FAIL"
    assert len(result["validation_findings"]) == 1

def test_DE_creditor_country_returns_success():
    state = {
        "payment_format": "SEPA",
        "parsed_fields": {
            "creditor_name": "John Smith",
            "creditor_iban": "GB29NWBK60161331926819",
            "creditor_bic": "BARCGB22",
            "debtor_name": "ACME Corp",
            "debtor_iban": "GB29NWBK60161331926819",
            "amount": "10000.00",
            "end_to_end_id": "E2E001",
            "ultimate_debtor_name": "ACME Corp Ltd",
            "remittance_info": "Invoice INV-001",
            "creditor_country": "DE"
        }
    }
    result = validate_fields(state)
    assert result["validation_status"] == "PASS"
    assert len(result["validation_findings"]) == 0

def test_remittance_info_returns_ambiguous():
    state = {
        "payment_format": "SEPA",
        "parsed_fields": {
            "creditor_name": "John Smith",
            "creditor_iban": "GB29NWBK60161331926819",
            "creditor_bic": "BARCGB22",
            "debtor_name": "ACME Corp",
            "debtor_iban": "GB29NWBK60161331926819",
            "amount": "10000.00",
            "end_to_end_id": "E2E001",
            "ultimate_debtor_name": "ACME Corp Ltd",
            "creditor_country": "GB"
        }
    }
    result = validate_fields(state)
    assert result["validation_status"] == "AMBIGUOUS"
    assert len(result["validation_findings"]) == 1


# Retrieve context tests
# A state with one FAIL finding returns one regulation clause
# A state with multiple findings returns matching number of clauses
# Each clause has all four fields — field, query, clause, source
# Routing — FAIL goes to generate_audit_report, AMBIGUOUS goes to human_review

def test_regulation_clause_return_success():
    state = {
        "payment_format": "SEPA",
        "validation_findings": [{
            "field": "creditor_name",
            "issue": "Creditor name is mandatory for all SEPA credit transfers (EPC133-08 AT-21)",
            "severity": "ERROR"
    }],
        "validation_status": "FAIL"

    }
    result = retrieve_context(state)
    assert len(result["regulation_context"]) == 1
    clause = result["regulation_context"][0]
    assert clause["field"] == "creditor_name"
    assert clause["query"] == "Creditor name is mandatory for all SEPA credit transfers (EPC133-08 AT-21)"
    assert clause["clause"] is not None
    assert clause["source"] is not None

def test_multiple_regulation_clause_return_success():
    state = {
        "payment_format": "SEPA",
        "validation_findings": [{
            "field": "creditor_name",
            "issue": "Creditor name is mandatory for all SEPA credit transfers (EPC133-08 AT-21)",
            "severity": "ERROR"
        }, {
            "field": "creditor_iban",
            "issue": "Creditor IBAN is mandatory and must pass ISO 13616 checksum (EPC133-08 AT-20)",
            "severity": "ERROR"
        }],
        "validation_status": "FAIL"

    }
    result = retrieve_context(state)
    assert len(result["regulation_context"]) == 2
    clause = result["regulation_context"][0]
    assert clause["field"] == "creditor_name"
    assert clause["query"] == "Creditor name is mandatory for all SEPA credit transfers (EPC133-08 AT-21)"
    assert clause["clause"] is not None
    assert clause["source"] is not None

    clause = result["regulation_context"][1]
    assert clause["field"] == "creditor_iban"
    assert clause["query"] == "Creditor IBAN is mandatory and must pass ISO 13616 checksum (EPC133-08 AT-20)"
    assert clause["clause"] is not None
    assert clause["source"] is not None

def test_route_after_retrieve_context_fail():
    state = {"validation_status": "FAIL"}
    assert route_after_retrieve(state) == "generate_audit_report"

def test_route_after_retrieve_context_ambiguous():
    state = {"validation_status": "AMBIGUOUS"}
    assert route_after_retrieve(state) == "human_review"