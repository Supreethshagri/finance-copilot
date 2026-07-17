from typing import TypedDict, Literal
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

from config import settings
from agents.sql_agent import run_sql_agent
from agents.analytics_agent import run_analytics_agent
from agents.expense_agent import run_expense_agent


router_llm = ChatGroq(model="openai/gpt-oss-20b",
                      api_key=settings.GROQ_API_KEY, temperature=0)


class AgentState(TypedDict):
    question: str
    user_id: int
    route: str
    result: dict


def route_node(state: AgentState) -> AgentState:
    """Ask the LLM which agent should handle this question."""
    prompt = f"""Classify the user's request into ONE route:
- "sql": specific data lookups (e.g. 'show my Amazon transactions', 'how much on Swiggy')
- "analytics": summaries/insights/overview (e.g. 'give me insights', 'how am I doing')
- "expense": categorizing/organizing transactions (e.g. 'categorize my spending')
- "report": generating a downloadable report/PDF (e.g. 'generate my report', 'download PDF')

Respond with only the route word.

Request: {state['question']}"""
    resp = router_llm.invoke([{"role": "user", "content": prompt}])
    raw = resp.content.strip().lower()

    route = "sql"
    for candidate in ("expense", "analytics", "report", "sql"):
        if candidate in raw:
            route = candidate
            break

    state["route"] = route
    return state


def decide(state: AgentState) -> str:
    route = state.get("route", "")
    if route not in ("sql", "analytics", "expense", "report"):
        return "sql"
    return route


# NOTE: agent nodes need the db session; we pass it via a closure factory below.
def build_graph(db: Session):
    def sql_node(state: AgentState) -> AgentState:
        state["result"] = run_sql_agent(state["question"], state["user_id"], db)
        return state

    def analytics_node(state: AgentState) -> AgentState:
        state["result"] = run_analytics_agent(state["user_id"], db)
        return state

    def expense_node(state: AgentState) -> AgentState:
        state["result"] = run_expense_agent(state["user_id"], db)
        return state
    
    def tax_node(state: AgentState) -> AgentState:
        state["result"] = run_tax_agent(state["user_id"], db)
        return state

    def report_node(state: AgentState) -> AgentState:
        # Report is a file download; signal the frontend to fetch /chat/report.
        state["result"] = {"action": "download_report",
                           "message": "Your report is ready to download."}
        return state

    graph = StateGraph(AgentState)
    graph.add_node("router", route_node)
    graph.add_node("sql", sql_node)
    graph.add_node("analytics", analytics_node)
    graph.add_node("expense", expense_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", decide,
                                {"sql": "sql", "analytics": "analytics",
                                 "expense": "expense","report": "report"})
    graph.add_edge("sql", END)
    graph.add_edge("analytics", END)
    graph.add_edge("expense", END)
    graph.add_edge("report", END)


    return graph.compile()


def run_supervisor(question: str, user_id: int, db: Session) -> dict:
    app = build_graph(db)
    final = app.invoke({"question": question, "user_id": user_id,
                        "route": "", "result": {}})
    return {"route_taken": final["route"], "result": final["result"]}