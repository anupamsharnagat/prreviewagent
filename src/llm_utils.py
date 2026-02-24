import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from src.schemas import DiffSummary, FootgunFinding, SecurityVulnerability
from typing import List

# Configure environment for local Ollama
os.environ['OPENAI_BASE_URL'] = 'http://localhost:11434/v1'
os.environ['OPENAI_API_KEY'] = 'ollama'

ollama_model = OpenAIModel('kimi-k2.5:cloud')

summary_agent = Agent(
    model=ollama_model,
    output_type=DiffSummary,
    retries=3,
    system_prompt=(
        "You are an expert code reviewer. Given a git diff, analyze it in depth and provide a structured summary. "
        "The 'executive_summary' should mention specific file names and the overall goal. "
        "The 'what_changed' list must include technical details about specific functions or code blocks modified. "
        "The 'impact_assessment' should evaluate how these changes affect the rest of the system. "
        "Respond ONLY with valid JSON matching the schema."
    )
)

footgun_agent = Agent(
    model=ollama_model,
    output_type=list[FootgunFinding],
    retries=3,
    system_prompt=(
        "You are an expert security and logic code reviewer. Given a git diff, analyze it for logical errors, "
        "race conditions, memory leaks, performance bottlenecks, or silent failures. "
        "BE VERY SPECIFIC. If you find an issue, include the exact file path and line number from the diff. "
        "Your 'suggestion' must include a technical explanation and, if possible, a small code snippet showing the fix. "
        "If there are no logic issues or potential 'footguns', return an empty list []. "
        "Your output must be a valid JSON list of objects. Respond ONLY with the JSON list."
    )
)

security_agent = Agent(
    model=ollama_model,
    output_type=list[SecurityVulnerability],
    retries=3,
    system_prompt=(
        "You are an expert security researcher. Analyze the following diff for common security vulnerabilities (OWASP Top 10). "
        "Look for: SQL Injection, XSS, Hardcoded Secrets, Path Traversal, Insecure Defaults, and Missing Auth. "
        "Identify the 'tool_source' as 'LLM_Security_Scan'. "
        "If there are no security vulnerabilities, return an empty list []. "
        "Respond ONLY with a valid JSON list of objects."
    )
)

def generate_diff_summary(diff_content: str) -> DiffSummary:
    result = summary_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.output

def generate_footguns(diff_content: str) -> list[FootgunFinding]:
    result = footgun_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.output

def generate_llm_security_findings(diff_content: str) -> list[SecurityVulnerability]:
    result = security_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.output
