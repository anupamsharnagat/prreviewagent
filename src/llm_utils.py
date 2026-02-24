import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from src.schemas import DiffSummary, FootgunFinding
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
        "If there are no logic issues or potential 'footguns', return an empty list []. "
        "Your output must be a valid JSON list of objects. Respond ONLY with the JSON list."
    )
)

def generate_diff_summary(diff_content: str) -> DiffSummary:
    result = summary_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.output

def generate_footguns(diff_content: str) -> list[FootgunFinding]:
    result = footgun_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.output
