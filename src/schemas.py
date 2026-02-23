from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class DiffSummary(BaseModel):
    executive_summary: str = Field(description="High-level overview of the PR.")
    what_changed: List[str] = Field(description="Bullet points of actual changes.")
    why_it_changed: str = Field(description="Inferred or stated motivation.")
    impact_assessment: str = Field(description="Potential impact on the wider system.")

class FootgunFinding(BaseModel):
    file_path: str
    line_number: int
    issue_type: str = Field(description="e.g., Race Condition, Memory Leak, Silent Exception, NullPointer, Off-By-One, etc.")
    description: str
    suggestion: str

class SecurityVulnerability(BaseModel):
    tool_source: str = Field(description="Semgrep (multi-language), Bandit (Python), or LLM Secret Scan")
    severity: str
    cwe: str
    file_path: str
    line_number: int
    description: str
    remediation: str

class SemanticImpactFinding(BaseModel):
    changed_function: str
    impacted_call_sites: List[str] = Field(description="Locations calling the changed function that need updates. Found via ripgrep/AST.")
    requires_update: bool

class PRReviewReport(BaseModel):
    pr_url: str
    summary: Optional[DiffSummary] = None
    footguns: List[FootgunFinding]
    security_issues: List[SecurityVulnerability]
    semantic_impacts: List[SemanticImpactFinding]
    external_context: Dict[str, str] = Field(description="Ground truth definitions for referenced utilities.")
