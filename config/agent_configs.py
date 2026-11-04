"""
CAPSTONE CONCEPTS DEMONSTRATED:
  - Agent Configurations: every agent has an explicit config (model, tokens, iterations)
  - Agent Model Mapping: cheap model for coordination, capable model for generation
"""
from dataclasses import dataclass


@dataclass
class AgentConfig:
    name: str
    model: str
    max_tokens: int
    max_iterations: int  # CAPSTONE: Hard Stop — every agent has an upper bound
    description: str


# CAPSTONE: Agent Model Mapping
# Rule: match model capability to the task's cognitive load, not just "use the best model"
#
# claude-haiku  → routing, coordination, simple classification (fast + cheap)
# claude-sonnet → generation, reasoning, review (quality output required)
# claude-opus   → reserved for complex enterprise reasoning (Expert eval only)

AGENT_CONFIGS: dict[str, AgentConfig] = {
    "orchestrator": AgentConfig(
        name="orchestrator",
        model="claude-haiku-4-5-20251001",   # coordinates only — no generation needed
        max_tokens=512,
        max_iterations=4,
        description="Coordinates pipeline phases and HITL gates. Never does QA work directly.",
    ),
    "analysis": AgentConfig(
        name="analysis",
        model="claude-sonnet-4-6",           # Phase 0+1 require structured reasoning
        max_tokens=3000,
        max_iterations=8,
        description="Phase 0: Classify requirement. Phase 1: Generate test plan.",
    ),
    "generation": AgentConfig(
        name="generation",
        model="claude-sonnet-4-6",           # Phase 2+3 generate and review test cases
        max_tokens=4000,
        max_iterations=8,
        description="Phase 2: Generate test cases. Phase 3: Review for gaps.",
    ),
    "automation": AgentConfig(
        name="automation",
        model="claude-sonnet-4-6",           # Phase 4+5 generate and review pytest code
        max_tokens=4000,
        max_iterations=8,
        description="Phase 4: Generate pytest automation. Phase 5: Review code quality.",
    ),
}
