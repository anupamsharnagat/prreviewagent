---
name: Stateful PR Reviewer
description: "A LangGraph-based agent that performs deep analysis on PRs (Semgrep/Bandit, AST impact, footgun detection) and pauses for Human-in-the-Loop review."
---

# Stateful PR Reviewer Skill

This skill allows an Antigravity agent to attach to a workspace, read PR diffs, and perform stateful, multi-step analysis before posting results to GitHub. It uses LangGraph for state management, meaning it can pause and wait for human approval.

## Prerequisites
- Python 3.10+
- The `prreviewsystem` backend must be initialized (dependencies installed in `.venv`).
- Ensure `GH_TOKEN` is set in the environment or `.env` for the MCP connection.

## Execution Workflow

When the user asks you to "Run the PR Reviewer" or "Review this PR", follow these steps carefully:

1. **Activate Environment**: Ensure you are running commands `e:\rnd\antigravity\prreviewsystem`
2. **Execute Agent**: Run the following command to start the LangGraph state machine:
   ```bash
   python -c "from src.agent import graph; print(graph.invoke({'pr_url': 'https://github.com/mock/repo/pull/1'}))"
   ```
3. **Wait for Checkpoint**: The execution will pause at the `human_approval` node.
4. **Prompt the User**: Present the findings generated in `reports/PR_Review.json` and `reports/PR_Review.md` to the user. Ask them if they approve the report.
5. **Resume Execution**: If the user approves, resume the graph execution by updating the state:
   ```bash
   python -c "from src.agent import graph; graph.update_state(<thread_id>, {'human_approved': True}); print(graph.invoke(None))"
   ```

## Testing / Browser-Use Verification

If evaluating this skill or verifying the workflow end-to-end, use the browser tool to confirm the final output:
1. Start the browser subagent using the `browser_subagent` tool.
2. Instruct the browser subagent to navigate to the target PR URL.
3. Verify that a comment by the "PR Review Agent" has been successfully posted containing the Executive Summary, Footguns, and Security vulnerabilities.
