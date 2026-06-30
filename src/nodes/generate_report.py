import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from src.state import PaymentComplianceState

load_dotenv()

SYSTEM_PROMPT = """You are a compliance audit assistant for a bank.
Write clear, factual audit reports for payment compliance reviews.
Do not make approval/rejection decisions — only document what happened
and why, based on the data provided. Be precise and reference specific
regulation clauses where available."""

USER_PROMPT_TEMPLATE = """Write a compliance audit report based on the
following payment review data:

{context}

The report should explain: what was checked, what (if anything) was
found, the regulatory basis for any findings, and the outcome of this
review. Keep it to 3-5 sentences, professional tone, suitable for a
compliance file."""


llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4o"),
    temperature=0
)

messages = [
    (
        "system",
        "You are a helpful assistant that translates English to French. Translate the user sentence.",
    ),
    ("human", "I love programming."),
]


def _call_llm(context: str) -> str:
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT_TEMPLATE.format(context = context))
    ]
    ai_msg = llm.invoke(messages)
    return ai_msg.content


def _build_context(state: PaymentComplianceState) -> str:
    parts = []
    
    parts.append(f"Payment format: {state.get('payment_format')}")
    
    if state.get("parse_status") == "ERROR":
        parts.append(f"Parse error: {state.get('parse_error')}")
        return "\n".join(parts)   # nothing else exists on this path
    
    parts.append(f"Parsed fields: {state.get('parsed_fields')}")
    
    findings = state.get("validation_findings", [])
    if findings:
        parts.append(f"Validation findings: {findings}")
    else:
        parts.append("Validation findings: none — payment passed all checks")
    
    if state.get("regulation_context"):
        parts.append(f"Regulation context: {state.get('regulation_context')}")
    
    if state.get("human_decision"):
        parts.append(f"Human reviewer decision: {state.get('human_decision')}")
        parts.append(f"Human reviewer notes: {state.get('human_notes')}")
    
    return "\n".join(parts)

def _determine_verdict(state: PaymentComplianceState) -> str:
    if state.get("parse_status") == "ERROR":
        return "REJECTED"
    if state.get("validation_status") == "PASS":
       return "APPROVED"
    if state.get("validation_status") == "FAIL":
        return "REJECTED"
    if state.get("human_decision") == "APPROVE":
        return "HUMAN_APPROVED"
    if state.get("human_decision") == "REJECT":
        return "HUMAN_REJECTED"
    return "UNKNOWN"

def generate_audit_report(state: PaymentComplianceState) -> dict:
    context = _build_context(state)
    response = _call_llm(context)
    verdict = _determine_verdict(state)

    return {
        "audit_report": response,
        "final_verdict": verdict
    }