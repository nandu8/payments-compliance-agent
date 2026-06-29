from src.state import PaymentComplianceState
from src.rules.sepa_rules import SEPA_RULES

# Checks whether there are any validation error for the fields in the rules
def validate_fields (state: PaymentComplianceState) -> dict:
    findings_list = []
    for rule in SEPA_RULES:
        if state.get("payment_format") not in rule.applies_to:
            continue
        if state.get("parsed_fields").get("creditor_country") not in rule.country_scope and "ALL" not in rule.country_scope :
            continue
        
        
        if not rule.check(state.get("parsed_fields")):            
            findings_list.append({
                "field" : rule.field,
                "issue" : rule.description,
                "severity" : rule.severity
            })

    if any(item["severity"] == "ERROR" for item in findings_list):
        status = "FAIL"
    elif any(item["severity"] == "WARNING" for item in findings_list):
        status = "AMBIGUOUS"
    else:
        status = "PASS"
    return {
                "validation_findings" : findings_list,
                "validation_status" : status
            }

#Condiional Edge
def route_after_validation(state: PaymentComplianceState) -> str:
    status = state["validation_status"]
    if status == "FAIL":
        return "retrieve_context"
    elif status == "AMBIGUOUS":
        return "human_review"
    else:
        return "generate_audit_report"