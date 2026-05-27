"""Taxonomy adapter for AgentBench benchmark results.

Maps AgentBench findings to the canonical ``mcp-taxonomy`` :class:`TaxonomyEvent`
format for cross-tool correlation in MCPscop and other ecosystem tools.
"""

from __future__ import annotations

from mcp_taxonomy import (
    AttackCategory,
    DetectionMethod,
    TaxonomyEvent,
)
from mcp_taxonomy import (
    Severity as TaxSeverity,
)
from mcp_taxonomy import severity_weight as tax_severity_weight

from agentbench.models import BenchmarkResult, ScoreReport, TestStatus

CATEGORY_ATTACK_MAP: dict[str, AttackCategory] = {
    "prompt_injection": AttackCategory.INJECTION,
    "tool_poisoning": AttackCategory.TOOL_POISONING,
    "ssrf": AttackCategory.SSRF,
    "jailbreak": AttackCategory.JAILBREAK,
    "data_exfiltration": AttackCategory.EXFILTRATION,
    "memory_attacks": AttackCategory.MISCONFIGURATION,
    "multi_agent": AttackCategory.IMPERSONATION,
    "mcp_attack": AttackCategory.TOOL_POISONING,
}

SEVERITY_MAP: dict[str, TaxSeverity] = {
    "critical": TaxSeverity.CRITICAL,
    "high": TaxSeverity.HIGH,
    "medium": TaxSeverity.MEDIUM,
    "low": TaxSeverity.LOW,
    "info": TaxSeverity.INFO,
}


def benchmark_result_to_taxonomy(result: BenchmarkResult) -> TaxonomyEvent:
    """Convert a single benchmark result to a canonical TaxonomyEvent.

    Args:
        result: A benchmark execution result.

    Returns:
        A :class:`mcp_taxonomy.TaxonomyEvent` instance.
    """
    category = result.test_case.category
    attack_cat = CATEGORY_ATTACK_MAP.get(category, AttackCategory.MISCONFIGURATION)
    passed = result.status == TestStatus.PASSED
    tax_sev = TaxSeverity.LOW if passed else TaxSeverity.HIGH
    risk_score = tax_severity_weight(tax_sev) * 2

    return TaxonomyEvent(
        source="agentbench",
        attack_category=attack_cat,
        severity=tax_sev,
        confidence=TaxSeverity.HIGH if not passed else TaxSeverity.MEDIUM,
        title=f"{'PASS' if passed else 'FAIL'}: {result.test_case.name}",
        description=result.test_case.description,
        recommendation="Review security controls" if not passed else "No action needed",
        detection_method=DetectionMethod.INJECTION_PATTERNS,
        target=result.test_case.target or "",
        snippet=result.response[:200],
        blocked=not passed,
        risk_score=risk_score,
        raw={
            "test_id": result.test_case.id,
            "category": category,
            "prompt": result.test_case.prompt[:500],
            "response_time_ms": result.response_time_ms,
            "error": result.error_message,
        },
    )


def report_to_taxonomy_events(report: ScoreReport) -> list[TaxonomyEvent]:
    """Convert an entire score report to a list of taxonomy events.

    Args:
        report: A complete score report.

    Returns:
        List of :class:`mcp_taxonomy.TaxonomyEvent` instances, one per failed test.
    """
    return [benchmark_result_to_taxonomy(r) for r in report.results if r.status == TestStatus.FAILED]


def taxonomy_event_to_dict(event: TaxonomyEvent) -> dict:
    """Serialize a TaxonomyEvent to a JSON-compatible dict.

    Args:
        event: The taxonomy event to serialize.

    Returns:
        Dict suitable for JSON serialization.
    """
    return {
        "source": event.source,
        "attack_category": event.attack_category.value if hasattr(event.attack_category, "value") else str(event.attack_category),
        "severity": event.severity.value if hasattr(event.severity, "value") else str(event.severity),
        "confidence": event.confidence.value if hasattr(event.confidence, "value") else str(event.confidence),
        "title": event.title,
        "description": event.description,
        "recommendation": event.recommendation,
        "detection_method": event.detection_method.value if hasattr(event.detection_method, "value") else str(event.detection_method),
        "target": event.target,
        "snippet": event.snippet,
        "blocked": event.blocked,
        "risk_score": event.risk_score,
        "raw": event.raw,
    }
