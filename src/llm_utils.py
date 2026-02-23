from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from src.schemas import DiffSummary, FootgunFinding
from typing import List

ollama_model = OpenAIModel(
    'kimi-k2.5',
    base_url='http://localhost:11434/v1',
    api_key='ollama',
)

summary_agent = Agent(
    model=ollama_model,
    result_type=DiffSummary,
    system_prompt=(
        "You are an expert code reviewer. Given a git diff, analyze it and provide a structured summary. "
        "Include an executive summary, list what changed, why it changed, and an impact assessment."
    )
)

footgun_agent = Agent(
    model=ollama_model,
    result_type=list[FootgunFinding],
    system_prompt=(
        "You are an expert security and logic code reviewer. Given a git diff, analyze it for logical errors, "
        "race conditions, memory leaks, or silent failures. If there are none, return an empty list. "
        "Provide line numbers referring precisely to the lines in the diff, file paths, and suggestions."
    )
)

def generate_diff_summary(diff_content: str) -> DiffSummary:
    result = summary_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.data

def generate_footguns(diff_content: str) -> list[FootgunFinding]:
    result = footgun_agent.run_sync(f"Diff to analyze:\n{diff_content}")
    return result.data
