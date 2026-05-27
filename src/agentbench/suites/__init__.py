"""Security benchmark suites for AgentBench."""

from agentbench.suites.data_exfiltration import DataExfiltrationSuite
from agentbench.suites.jailbreak import JailbreakSuite
from agentbench.suites.mcp_attack import MCPAttackSuite
from agentbench.suites.memory_attacks import MemoryAttackSuite
from agentbench.suites.multi_agent import MultiAgentSuite
from agentbench.suites.prompt_injection import PromptInjectionSuite
from agentbench.suites.ssrf import SSRFSuite
from agentbench.suites.tool_poisoning import ToolPoisoningSuite

SUITE_REGISTRY: dict[str, type] = {
    "prompt_injection": PromptInjectionSuite,
    "tool_poisoning": ToolPoisoningSuite,
    "ssrf": SSRFSuite,
    "data_exfiltration": DataExfiltrationSuite,
    "jailbreak": JailbreakSuite,
    "memory_attacks": MemoryAttackSuite,
    "multi_agent": MultiAgentSuite,
    "mcp_attack": MCPAttackSuite,
}


def get_suite_names() -> list[str]:
    """Return list of available suite names."""
    return list(SUITE_REGISTRY.keys())


def get_suite(name: str) -> type:
    """Get a suite class by name.

    Args:
        name: Suite name (e.g., 'prompt_injection').

    Returns:
        Suite class.

    Raises:
        KeyError: If suite name is not found.
    """
    if name not in SUITE_REGISTRY:
        raise KeyError(f"Unknown suite: {name}. Available: {', '.join(SUITE_REGISTRY)}")
    return SUITE_REGISTRY[name]


__all__ = [
    "DataExfiltrationSuite",
    "JailbreakSuite",
    "MCPAttackSuite",
    "MemoryAttackSuite",
    "MultiAgentSuite",
    "PromptInjectionSuite",
    "SSRFSuite",
    "SUITE_REGISTRY",
    "ToolPoisoningSuite",
    "get_suite",
    "get_suite_names",
]
