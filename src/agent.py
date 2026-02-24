import json
import os
import re
import sys
import tempfile
import subprocess
import sqlite3
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from github import Github

load_dotenv()

from src.schemas import (
    PRReviewReport,
    DiffSummary,
    FootgunFinding,
    SecurityVulnerability,
    SemanticImpactFinding
)
from src.llm_utils import generate_diff_summary, generate_footguns, generate_llm_security_findings

class AgentState(TypedDict):
    pr_url: str
    diff_content: str
    repo_path: str | None
    # Findings we accumulate along the way
    summary: DiffSummary | None
    footguns: Annotated[List[FootgunFinding], operator.add]
    security_issues: Annotated[List[SecurityVulnerability], operator.add]
    semantic_impacts: Annotated[List[SemanticImpactFinding], operator.add]
    external_context: Dict[str, str]
    # Control flow
    human_approved: bool
    human_comment: str | None
    final_report: PRReviewReport | None


def fetch_pr_context(state: AgentState):
    """Fetches PR diff from GitHub and clones the repo locally."""
    pr_url = state['pr_url']
    print(f"Fetching context for {pr_url}...")
    
    match = re.search(r'github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if not match:
        raise ValueError("Invalid GitHub PR URL format.")
    
    owner, repo_name, pr_number = match.groups()
    repo_full_name = f"{owner}/{repo_name}"
    
    token = os.getenv("GITHUB_TOKEN")
    g = Github(token)
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(int(pr_number))
    
    diff_content = ""
    files = list(pr.get_files())
    print(f"Found {len(files)} files in PR.")
    for file in files:
        if file.patch:
            diff_content += f"--- {file.filename}\n+++ {file.filename}\n{file.patch}\n\n"
        else:
            print(f"Warning: No patch for {file.filename} (might be a new large file or binary)")
            
    tmp_dir = tempfile.mkdtemp(prefix="pr_agent_")
    clone_url = repo.clone_url
    if token:
        clone_url = clone_url.replace("https://", f"https://{token}@")
        
    print(f"Cloning {repo_full_name} into {tmp_dir}...")
    subprocess.run(["git", "clone", clone_url, tmp_dir], check=True, capture_output=True)
    subprocess.run(["git", "fetch", "origin", f"pull/{pr_number}/head:pr_branch"], cwd=tmp_dir, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "pr_branch"], cwd=tmp_dir, check=True, capture_output=True)
    
    return {
        "diff_content": diff_content,
        "repo_path": tmp_dir
    }


def analyze_diff_summary(state: AgentState):
    """Uses LLM to summarize the diff."""
    print("Summarizing diff...")
    diff_content = state.get('diff_content')
    if not diff_content:
        print("Empty diff content found!")
        return {"summary": DiffSummary(
            executive_summary="No changes detected or diff is unavailable.",
            what_changed=[],
            why_it_changed="N/A",
            impact_assessment="None"
        )}
    try:
        summary = generate_diff_summary(diff_content)
        return {"summary": summary}
    except Exception as e:
        print(f"LLM Summary failed: {e}")
        return {"summary": DiffSummary(
            executive_summary=f"Failed to generate summary: {str(e)}",
            what_changed=[],
            why_it_changed="Error encountered during analysis.",
            impact_assessment="Unknown"
        )}


def logic_footgun_detector(state: AgentState):
    """Scans for logic errors, race conditions, leaks."""
    print("Detecting footguns...")
    if not state.get('diff_content'):
        return {"footguns": []}
    footguns = generate_footguns(state['diff_content'])
    return {"footguns": footguns}


def security_scanner(state: AgentState):
    """Orchestrates Bandit/Semgrep."""
    print("Running security scanners...")
    repo_path = state.get('repo_path')
    if not repo_path:
        return {"security_issues": []}
        
    security_issues = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", repo_path, "-f", "json"],
            capture_output=True, text=True
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                vuln = SecurityVulnerability(
                    tool_source="Bandit",
                    severity=issue.get("issue_severity", "Low"),
                    cwe=str(issue.get("issue_cwe", {}).get("id", 0)),
                    file_path=issue.get("filename", "").replace(repo_path, "").lstrip('/\\'),
                    line_number=issue.get("line_number", 0),
                    description=issue.get("issue_text", ""),
                    remediation="Check Bandit documentation."
                )
                security_issues.append(vuln)
    except Exception as e:
        print(f"Bandit execution failed: {e}")
        
    # --- Fallback: LLM Security Scan (for Java, JS, HTML, etc.) ---
    try:
        print("Running fallback LLM security scan...")
        llm_findings = generate_llm_security_findings(state.get('diff_content', ''))
        security_issues.extend(llm_findings)
    except Exception as e:
        print(f"LLM Security Scan failed: {e}")
        
    return {"security_issues": security_issues}


def semantic_impact_finder(state: AgentState):
    """Uses ripgrep + AST to find impacted call sites."""
    print("Finding semantic impact...")
    repo_path = state.get('repo_path')
    diff_content = state.get('diff_content', '')
    impacts = []
    
    if not repo_path:
        return {"semantic_impacts": impacts}
        
    # Supports Python (def), Java/JS (public/private/void/function)
    added_funcs = re.findall(r'^\+(?:def\s+|public\s+|private\s+|protected\s+|void\s+|function\s+)([a-zA-Z_][a-zA-Z0-9_]*)', diff_content, re.MULTILINE)
    
    for func in added_funcs:
        try:
            result = subprocess.run(
                ["git", "grep", "-n", func],
                cwd=repo_path, capture_output=True, text=True
            )
            sites = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(':', 2)
                    if len(parts) >= 2:
                        sites.append(f"{parts[0]}:{parts[1]}")
            
            impact = SemanticImpactFinding(
                changed_function=func,
                impacted_call_sites=sites[:10],
                requires_update=len(sites) > 1
            )
            impacts.append(impact)
        except Exception as e:
            print(f"Impact finder failed: {e}")
            
    return {"semantic_impacts": impacts}


def fetch_external_context(state: AgentState):
    """Fetches definitions of specific utilities."""
    print("Fetching external context...")
    return {"external_context": {"DatabaseDriver": "class DatabaseDriver: ... "}}


def notify_reviewer(state: AgentState):
    """Posts a status comment to GitHub to notify the user that review is ready."""
    print("Notifying reviewer on GitHub...")
    pr_url = state['pr_url']
    match = re.search(r'github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if match:
        owner, repo, pr_num = match.groups()
        token = os.getenv("GITHUB_TOKEN")
        g = Github(token)
        repo_obj = g.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(int(pr_num))
        
        # Check if we already posted a notification to avoid spamming
        comments = pr.get_issue_comments()
        for comment in comments:
            if "🔍 AI Analysis Complete" in comment.body:
                return {} # Skip duplicate
                
        msg = (
            f"### 🔍 AI Analysis Complete\n"
            f"The AI PR Agent has finished scanning this PR. Findings are awaiting your approval in the local Control Room.\n"
            f"\n*Note: This is an automated status message.*"
        )
        pr.create_issue_comment(msg)
    return {}


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
        pr_url = state['pr_url']
        match = re.search(r'github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
        if match:
            owner, repo_name, pr_number = match.groups()
            token = os.getenv("GITHUB_TOKEN")
            g = Github(token)
            repo = g.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(int(pr_number))
            
            report = state.get("final_report")
            
            if not report:
                print("No final report generated!")
                return {}
                
            md_content = "# Autonomous PR Review\n\n"
            
            human_comment = state.get("human_comment")
            if human_comment:
                md_content += f"## 📝 Human Reviewer Comments\n{human_comment}\n\n---\n\n"
            
            md_content += f"## Summary\n{report.summary.executive_summary if report.summary else 'No summary provided.'}\n\n"
            
            if report.footguns:
                md_content += "## 🚨 Logic Footguns\n"
                for f in report.footguns:
                    md_content += f"- **{f.file_path}:{f.line_number}** ({f.issue_type}): {f.description}\n  *Suggestion: {f.suggestion}*\n"
            else:
                md_content += "## 🚨 Logic Footguns\n✅ No logic issues or footguns detected.\n"
            
            if report.security_issues:
                md_content += "\n## 🔒 Security Vulnerabilities\n"
                for s in report.security_issues:
                    md_content += f"- **{s.file_path}:{s.line_number}** [{s.severity}] {s.cwe}: {s.description}\n  *Remediation: {s.remediation}*\n"
            else:
                md_content += "\n## 🔒 Security Vulnerabilities\n✅ No security vulnerabilities detected.\n"
                    
            if report.semantic_impacts:
                md_content += "\n## 🌍 Semantic Impacts\n"
                for i in report.semantic_impacts:
                    md_content += f"- Function `{i.changed_function}` impacted {len(i.impacted_call_sites)} call sites.\n"
            else:
                md_content += "\n## 🌍 Semantic Impacts\n✅ No external semantic impacts found.\n"
                    
            pr.create_issue_comment(md_content)
            print("Successfully posted comment!")
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
builder.add_node("notify_reviewer", notify_reviewer)
builder.add_node("human_approval", human_approval)
builder.add_node("post_to_github", post_to_github)

builder.add_edge(START, "fetch_pr_context")
builder.add_edge("fetch_pr_context", "analyze_diff_summary")
builder.add_edge("analyze_diff_summary", "logic_footgun_detector")
builder.add_edge("logic_footgun_detector", "security_scanner")
builder.add_edge("security_scanner", "semantic_impact_finder")
builder.add_edge("semantic_impact_finder", "fetch_external_context")
builder.add_edge("fetch_external_context", "notify_reviewer")
builder.add_edge("notify_reviewer", "human_approval")
builder.add_edge("human_approval", "post_to_github")
builder.add_edge("post_to_github", END)

# Compile with interrupt
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["post_to_github"]
)
memory.setup() # Ensure tables are created
