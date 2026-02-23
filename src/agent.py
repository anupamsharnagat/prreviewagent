import json
from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.schemas import (
    PRReviewReport,
    DiffSummary,
    FootgunFinding,
    SecurityVulnerability,
    SemanticImpactFinding
)

class AgentState(TypedDict):
    pr_url: str
    diff_content: str
    # Findings we accumulate along the way
    summary: DiffSummary | None
    footguns: Annotated[List[FootgunFinding], operator.add]
    security_issues: Annotated[List[SecurityVulnerability], operator.add]
    semantic_impacts: Annotated[List[SemanticImpactFinding], operator.add]
    external_context: Dict[str, str]
    # Control flow
    human_approved: bool
    final_report: PRReviewReport | None


def fetch_pr_context(state: AgentState):
    """Mock node to fetch PR details from GitHub."""
    print(f"Fetching context for {state['pr_url']}...")
    # In a real scenario, use GitHub MCP here
    return {
        "diff_content": "def example_function():\n    pass # Added new feature\n",
    }


def analyze_diff_summary(state: AgentState):
    """Uses LLM to summarize the diff."""
    print("Summarizing diff...")
    # Mock LLM call with PydanticAI
    summary = DiffSummary(
        executive_summary="Added example function.",
        what_changed=["New example_function defined."],
        why_it_changed="Implementation of new feature.",
        impact_assessment="Low impact, isolated change."
    )
    return {"summary": summary}


def logic_footgun_detector(state: AgentState):
    """Scans for logic errors, race conditions, leaks."""
    print("Detecting footguns...")
    # Mock finding
    finding = FootgunFinding(
        file_path="src/main.py",
        line_number=10,
        issue_type="Silent Exception",
        description="Try-except block swallows exception without logging.",
        suggestion="Add a logger.error() call inside the except block."
    )
    return {"footguns": [finding]}


def security_scanner(state: AgentState):
    """Orchestrates Bandit/Semgrep."""
    print("Running security scanners...")
    vuln = SecurityVulnerability(
        tool_source="Semgrep",
        severity="Medium",
        cwe="CWE-79",
        file_path="src/api.py",
        line_number=42,
        description="Potential XSS vulnerability in endpoint.",
        remediation="Sanitize user input before rendering."
    )
    return {"security_issues": [vuln]}


def semantic_impact_finder(state: AgentState):
    """Uses ripgrep + AST to find impacted call sites."""
    print("Finding semantic impact...")
    impact = SemanticImpactFinding(
        changed_function="example_function",
        impacted_call_sites=["src/utils.py:20"],
        requires_update=False
    )
    return {"semantic_impacts": [impact]}


def fetch_external_context(state: AgentState):
    """Fetches definitions of specific utilities."""
    print("Fetching external context...")
    return {"external_context": {"DatabaseDriver": "class DatabaseDriver: ... "}}


def human_approval(state: AgentState):
    """Checkpoint node where execution pauses for human approval."""
    print("\n--- HUMAN REVIEW REQUIRED ---")
    print(f"Summary: {state['summary'].title() if hasattr(state['summary'], 'title') else state['summary']}")
    print(f"Footguns Found: {len(state['footguns'])}")
    print(f"Security Issues Found: {len(state['security_issues'])}")
    print("-----------------------------\n")
    # Generating the artifact
    report = PRReviewReport(
        pr_url=state['pr_url'],
        summary=state['summary'],
        footguns=state['footguns'],
        security_issues=state['security_issues'],
        semantic_impacts=state['semantic_impacts'],
        external_context=state.get('external_context', {})
    )
    
    with open(f"reports/PR_Review.json", "w") as f:
        f.write(report.model_dump_json(indent=2))
        
    return {"final_report": report}


def post_to_github(state: AgentState):
    """Posts the final report to GitHub if approved."""
    if state.get("human_approved"):
        print(f"Posting final report to GitHub PR: {state['pr_url']}...")
        return {}
    else:
        print("Review was rejected or not approved. Aborting GitHub post.")
        return {}


# --- Build Graph ---
builder = StateGraph(AgentState)

builder.add_node("fetch_pr_context", fetch_pr_context)
builder.add_node("analyze_diff_summary", analyze_diff_summary)
builder.add_node("logic_footgun_detector", logic_footgun_detector)
builder.add_node("security_scanner", security_scanner)
builder.add_node("semantic_impact_finder", semantic_impact_finder)
builder.add_node("fetch_external_context", fetch_external_context)
builder.add_node("human_approval", human_approval)
builder.add_node("post_to_github", post_to_github)

builder.add_edge(START, "fetch_pr_context")
builder.add_edge("fetch_pr_context", "analyze_diff_summary")
builder.add_edge("analyze_diff_summary", "logic_footgun_detector")
builder.add_edge("logic_footgun_detector", "security_scanner")
builder.add_edge("security_scanner", "semantic_impact_finder")
builder.add_edge("semantic_impact_finder", "fetch_external_context")
builder.add_edge("fetch_external_context", "human_approval")
builder.add_edge("human_approval", "post_to_github")
builder.add_edge("post_to_github", END)

# Compile with interrupt
memory = MemorySaver()
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["post_to_github"]
)
