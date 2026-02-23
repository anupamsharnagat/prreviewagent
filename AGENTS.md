# 🧠 PR Review Agent: Intelligence Documentation

This document describes the "brain" of the PR Review System, detailing the LangGraph architecture, state management, and the logic behind each analysis node.

## 🏗️ Architecture: LangGraph State Machine

The system is built as a stateful directed graph. Each node represents a specific step in the analysis process, and all nodes contribute to a shared `AgentState`.

### The `AgentState`
The state is the "memory" of the agent during a single review run.
```python
class AgentState(TypedDict):
    pr_url: str                # Target GitHub PR
    diff_content: str          # Raw Git diff text
    repo_path: str             # Local clone location
    summary: DiffSummary       # Executive summary (LLM)
    footguns: List[Footgun]    # Logic/Race condition findings (LLM)
    security_issues: List[Sec] # Bandit/Semgrep findings
    semantic_impacts: List[Imp]# Ripgrep-found call site changes
    human_approved: bool       # HIL Checkpoint status
    human_comment: str         # Optional user feedback
```

---

## 🧭 Graph Nodes & Logic

### 1. `fetch_pr_context`
- **Tooling**: `PyGithub`
- **Logic**: Connects to GitHub API, retrieves the PR diff (handling multiple files), and clones the repository to a temporary local directory for deep scanning.

### 2. `analyze_diff_summary`
- **Model**: Ollama (`kimi-k2.5:cloud`) via `PydanticAI`
- **Goal**: Provides a structured executive summary. It is prompted to identify file-level changes and the high-level intent of the PR.

### 3. `logic_footgun_detector`
- **Model**: Ollama (`kimi-k2.5:cloud`) via `PydanticAI`
- **Goal**: Specifically scans for "logical footguns" like race conditions, silent failures, or memory leaks that static analyzers often miss.

### 4. `security_scanner`
- **Tooling**: `Bandit`
- **Logic**: Executes local security scans on the cloned source code. It filters and maps tool output into the shared state.

### 5. `semantic_impact_finder`
- **Tooling**: `ripgrep`
- **Logic**: Parses the diff to find changed functions and then uses `ripgrep` to find all call sites in the repository that might be impacted by these changes.

### 6. `human_approval` (Checkpoint)
- **UI**: Streamlit
- **Logic**: Reconstructs the `PRReviewReport` from the accumulated state. It halts execution using LangGraph's `interrupt_before` mechanism, waiting for a human to review the findings in the UI.

### 7. `post_to_github`
- **Action**: GitHub API Comment
- **Logic**: Finalizes the structured report into Markdown. If a `human_comment` was provided in the UI, it prepends it to the automated report.

---

## 🛡️ Schemas & Governance

We use **Pydantic** models to ensure the LLM never produces "hallucinated" structures. All tool outputs are validated against the models in `src/schemas.py`.

- `DiffSummary`: Ensures the summary always has an impact assessment.
- `FootgunFinding`: Forces the LLM to provide a file path and exact line number.
- `SecurityVulnerability`: Maps disparate tool outputs into a unified format.

---

## 🛠️ Configuration
The agent is configured to point at a local Ollama instance by default:
- **Base URL**: `http://localhost:11434/v1`
- **Model**: `kimi-k2.5:cloud`
