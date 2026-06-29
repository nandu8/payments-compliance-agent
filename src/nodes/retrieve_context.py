from src.state import PaymentComplianceState

def _call_rag_stub(query: str) -> dict:
    # fake RAG response for now

    return {
        "answer": "According to EPC133-08 AT-21, the Creditor Name is a mandatory attribute in SEPA Credit Transfer transactions",
        "source": "SEPA EPC133-08"
    }


# TODO: replace _call_rag_stub with _call_rag_api once RAG app is available
# def _call_rag_api(query: str) -> dict:
    # real httpx call to your FastAPI RAG endpoint



def retrieve_context(state: PaymentComplianceState) -> dict:
    # loops through findings, calls stub, returns regulation_context

    regulation = []

    for finding in state.get('validation_findings'):
        response = _call_rag_stub(finding.get('issue'))
        regulation.append({
            "field" : finding.get('field'),
            "query" : finding.get('issue'),
            "clause" : response.get("answer"),
            "source" : response.get("source")
        })

    return { "regulation_context": regulation}

def route_after_retrieve(state: PaymentComplianceState) -> str:
    status = state.get('validation_status')
    if status == "FAIL":
        return "generate_audit_report"
    else:
        return "human_review"
