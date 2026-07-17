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

Respond with only the route word.

Request: {state['question']}"""
    resp = router_llm.invoke([{"role": "user", "content": prompt}])
    route = resp.content.strip().lower()
    if route not in ("sql", "analytics", "expense"):
        route = "sql"  # safe default
    state["route"] = route
    return state


def decide(state: AgentState) -> Literal["sql", "analytics", "expense"]:
    return state["route"]  # conditional edge reads the chosen route


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

    graph = StateGraph(AgentState)
    graph.add_node("router", route_node)
    graph.add_node("sql", sql_node)
    graph.add_node("analytics", analytics_node)
    graph.add_node("expense", expense_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", decide,
                                {"sql": "sql", "analytics": "analytics",
                                 "expense": "expense"})
    graph.add_edge("sql", END)
    graph.add_edge("analytics", END)
    graph.add_edge("expense", END)
    return graph.compile()


def run_supervisor(question: str, user_id: int, db: Session) -> dict:
    app = build_graph(db)
    final = app.invoke({"question": question, "user_id": user_id,
                        "route": "", "result": {}})
    return {"route_taken": final["route"], "result": final["result"]}