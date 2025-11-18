"""Agents package."""

# Re-export common agents for convenient imports
try:
	from .crewai_agent.agent import CrewAIAgent  # noqa: F401
except Exception:
	CrewAIAgent = None  # type: ignore

try:
	from .adk_agent.agent import ADKAgent  # noqa: F401
except Exception:
	ADKAgent = None  # type: ignore

try:
	from .research_agent.agent import ResearchAgent  # noqa: F401
except Exception:
	ResearchAgent = None  # type: ignore

