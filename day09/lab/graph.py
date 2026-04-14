"""
# graph.py — Multi-Agent Orchestrator (LangGraph)
# Author: Vu Viet Dung
# Sprint 1-4: Orchestration, Routing, and HITL Logic.
"""

import os
import sys
import io
import time
import json
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import dotenv

dotenv.load_dotenv(override=True)

# Fix encoding issue for Vietnamese characters on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except AttributeError:
        pass

# ─────────────────────────────────────────────
# 1. State Schema
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    task: str
    retrieved_chunks: list
    retrieved_sources: list
    policy_result: dict
    mcp_tools_used: list
    final_answer: str
    confidence: float
    sources: list
    supervisor_route: str
    route_reason: str
    workers_called: list
    hitl_triggered: bool
    history: list
    worker_io_logs: list
    latency_ms: int
    needs_tool: bool
    risk_high: bool

# ─────────────────────────────────────────────
# 2. Nodes: Workers
# ─────────────────────────────────────────────
# Import trực tiếp hàm `run` có sẵn từ Sprint 2
from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run

def retrieval_node(state: AgentState) -> AgentState:
    return retrieval_run(state)

def policy_tool_node(state: AgentState) -> AgentState:
    return policy_tool_run(state)

def synthesis_node(state: AgentState) -> AgentState:
    return synthesis_run(state)

def human_review_node(state: AgentState) -> AgentState:
    """Xử lý các tình huống nhạy cảm cần Human in the loop."""
    state.setdefault("workers_called", []).append("human_review")
    state.setdefault("history", []).append("[human_review] Agent paused, requires external review.")
    state["hitl_triggered"] = True
    state["final_answer"] = "[HITL_PAUSED] Yêu cầu chuyển cho con người xem xét."
    state["confidence"] = 1.0
    return state

# ─────────────────────────────────────────────
# 3. Node: Supervisor (LLM Router)
# ─────────────────────────────────────────────
class RouteDecision(BaseModel):
    next_node: str = Field(
        description="The next worker to call. Must be precisely ONE of these strings: 'retrieval_worker', 'policy_tool_worker', 'human_review'"
    )
    reason: str = Field(description="A brief explanation in Vietnamese for why this node was chosen")
    needs_tool: bool = Field(description="Set to true if this task needs ticketing Mock tools or access to MCP server")
    risk_high: bool = Field(description="Set to true if this is an after-hours emergency or P1 incident that mentions ERR_ ")

def supervisor_node(state: AgentState) -> AgentState:
    """Sử dụng GPT-4o-mini để xử lý định tuyến (Routing)."""
    task = state.get("task", "")
    
    state.setdefault("history", []).append(f"[{datetime.now().time()}] Task received: {task}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith("sk-"):
        # Fallback to Heuristic nếu không setup Key (Giống bản Manual trước)
        task_lower = task.lower()
        if "err" in task_lower and ("không" in task_lower or "2am" in task_lower):
            route = "human_review"
            reason = "[Heuristic Fallback] Tự động route sang Human vì risk cao (Emergency)."
            needs_tool = False
        elif "hoàn tiền" in task_lower or "chính sách" in task_lower or "quyền" in task_lower or "level" in task_lower:
            route = "policy_tool_worker"
            reason = "[Heuristic Fallback] Pipeline tự động kích hoạt Policy Tool."
            needs_tool = True
        else:
            route = "retrieval_worker"
            reason = "[Heuristic Fallback] Request tìm kiếm tĩnh."
            needs_tool = False
            
        state["supervisor_route"] = route
        state["route_reason"] = reason
        state["needs_tool"] = needs_tool
        state["risk_high"] = False
        state["history"].append(f"[supervisor] Fallback Heuristic -> {route}")
        return state

    try:
        # LLM Logic Routing
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm = llm.with_structured_output(RouteDecision)
        
        system_prompt = (
            "Bạn là Supervisor Agent của nhóm IT Helpdesk. Nhiệm vụ của bạn là định tuyến công việc dựa trên ngữ cảnh người dùng cung cấp.\n"
            "- Nếu user hỏi đáp kiến thức chung chung (SLA là bao nhiêu, giờ làm việc v.v): định tuyến 'retrieval_worker'.\n"
            "- Nếu user đòi HOÀN TIỀN (refund), CHÍNH SÁCH ĐỔI TRẢ, NÂNG QUYỀN TRUY CẬP (Access Level), TẠO TICKET, hoặc hỏi QUY TRÌNH XỬ LÝ SỰ CỐ (SLA Procedures): định tuyến 'policy_tool_worker' và set needs_tool=true. Kể cả khi có yếu tố 2AM hay khẩn cấp, nếu user hỏi về QUY TRÌNH/CHÍNH SÁCH, hãy ưu tiên bộ phân này để tra cứu SOP.\n"
            "- Nếu là trường hợp nghiêm trọng ngoài hệ thống, lỗi CHƯA XÁC ĐỊNH (Undetermined Crashes) hoặc yêu cầu can thiệp trực tiếp không qua quy trình: định tuyến 'human_review'.\n"
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task}")
        ]
        
        decision = structured_llm.invoke(messages)
        
        # Security Fallback map
        route = decision.next_node
        if route not in ["retrieval_worker", "policy_tool_worker", "human_review"]:
            route = "retrieval_worker"
            
        state["supervisor_route"] = route
        # Thêm tag để dễ nhận biết LLM đang chạy
        state["route_reason"] = "[LangGraph LLM Router] " + decision.reason
        state["needs_tool"] = decision.needs_tool
        state["risk_high"] = decision.risk_high
        
    except Exception as e:
        state["supervisor_route"] = "retrieval_worker"
        state["route_reason"] = f"[LLM ERROR] Chặn lỗi model OpenAI timeout: {e}"
        state["needs_tool"] = False
        state["risk_high"] = False
        
    state["history"].append(f"[supervisor] LLM Routed -> {state['supervisor_route']}")
    return state

# ─────────────────────────────────────────────
# 4. Compile StateGraph
# ─────────────────────────────────────────────

def define_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_node)
    workflow.add_node("policy_tool_worker", policy_tool_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis_worker", synthesis_node)
    
    # ─── Edges ───
    workflow.add_edge(START, "supervisor")
    
    def route_condition(state: AgentState) -> str:
        return state.get("supervisor_route", "retrieval_worker")
        
    workflow.add_conditional_edges(
        "supervisor", 
        route_condition, 
        {
            "retrieval_worker": "retrieval_worker",
            "policy_tool_worker": "policy_tool_worker",
            "human_review": "human_review"
        }
    )
    
    # Từ các worker tìm kiếm / check policy -> Tổng hợp Output
    workflow.add_edge("retrieval_worker", "synthesis_worker")
    workflow.add_edge("policy_tool_worker", "synthesis_worker")
    
    # Từ human output / synthesis là xong process
    workflow.add_edge("human_review", END)
    workflow.add_edge("synthesis_worker", END)
    
    return workflow.compile()

app = define_graph()

# ─────────────────────────────────────────────
# 5. Pipeline Entry API & Utils
# ─────────────────────────────────────────────

def run_graph(task: str) -> dict:
    """Interface tiêu chuẩn được gọi từ eval_trace.py."""
    start_time = time.time()
    
    initial_state = {
        "task": task,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "confidence": 0.0,
        "sources": [],
        "supervisor_route": "unknown",
        "route_reason": "",
        "workers_called": [],
        "hitl_triggered": False,
        "history": [],
        "worker_io_logs": [],
        "latency_ms": 0,
        "needs_tool": False,
        "risk_high": False
    }

    final_state = app.invoke(initial_state)
    
    end_time = time.time()
    final_state["latency_ms"] = int((end_time - start_time) * 1000)
    
    return final_state

def save_trace(state: dict, output_dir: str = "artifacts/traces") -> str:
    """Lưu trace file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_task = state.get("task", "unknown")[:20].replace(" ", "_").replace("/", "").replace("?", "")
    filename = f"trace_{timestamp}_{safe_task}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        
    return filepath

# ─────────────────────────────────────────────
# 6. Standalone Runner
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Agent Graph Pipeline (LangGraph Edition)")
    print("=" * 60)
    
    test_queries = [
        "Quy định hoàn tiền Flash Sale như thế nào?",
        "SLA ticket P1 là bao lâu?",
        "Hệ thống sập lúc 2AM sáng, ticket ERR-999 cần xử lý khẩn không?"
    ]
    
    for q in test_queries:
        print(f"\n| USER MOCK: {q}")
        result = run_graph(q)
        print(f"| Route by: {result['supervisor_route']} ({result['route_reason']})")
        print(f"| Final Answer: {result['final_answer']}")
        print("-" * 40)
