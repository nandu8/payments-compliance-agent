from langgraph.types import interrupt
from src.state import PaymentComplianceState

def human_review(state: PaymentComplianceState) -> dict :

    interrupt({
        "message": "Payment requires compliance officer review",
        "validation_findings": state.get("validation_findings"),
        "regulation_context": state.get("regulation_context")
    })

    return {
        "human_decision": state.get("human_decision"),
        "human_notes": state.get("human_notes")
    }