from langgraph.graph import StateGraph, START, END
from src.state import PaymentComplianceState
from langgraph.checkpoint.memory import MemorySaver
from src.nodes import generate_report, human_review, parse_payment, retrieve_context, validate_fields

graph = StateGraph(PaymentComplianceState)


graph.add_node("parse_payment", parse_payment.parse_payment)
graph.add_node("validate_fields", validate_fields.validate_fields)
graph.add_node("retrieve_context", retrieve_context.retrieve_context)
graph.add_node("human_review", human_review.human_review)
graph.add_node("generate_report", generate_report.generate_audit_report)


graph.add_edge(START, "parse_payment")
graph.add_edge("human_review", "generate_report")
graph.add_edge("generate_report", END)


graph.add_conditional_edges(
    "parse_payment",
    parse_payment.route_after_parse,
    {
        "validate_fields": "validate_fields",
        "generate_audit_report": "generate_report"
    }
)

graph.add_conditional_edges(
    "validate_fields",
    validate_fields.route_after_validation,
    {
        "retrieve_context": "retrieve_context",
        "human_review": "human_review",
        "generate_audit_report": "generate_report"
    }
)

graph.add_conditional_edges(
    "retrieve_context",
    retrieve_context.route_after_retrieve,
    {
        "generate_audit_report": "generate_report",
        "human_review": "human_review",
    }
)

checkpointer = MemorySaver()
compiled_graph = graph.compile(checkpointer=checkpointer)