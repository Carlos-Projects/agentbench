"""Tests for benchmark suites."""

import pytest

from agentbench.suites import (
    SUITE_REGISTRY,
    DataExfiltrationSuite,
    JailbreakSuite,
    MemoryAttackSuite,
    MultiAgentSuite,
    PromptInjectionSuite,
    SSRFSuite,
    ToolPoisoningSuite,
    get_suite,
    get_suite_names,
)
from agentbench.suites.base import BaseSuite


class TestSuiteRegistration:
    def test_all_suites_registered(self) -> None:
        assert len(SUITE_REGISTRY) == 8

    def test_suite_names(self) -> None:
        names = get_suite_names()
        assert "prompt_injection" in names
        assert "tool_poisoning" in names
        assert "ssrf" in names
        assert "data_exfiltration" in names
        assert "jailbreak" in names
        assert "memory_attacks" in names
        assert "multi_agent" in names

    def test_get_suite_valid(self) -> None:
        cls = get_suite("prompt_injection")
        assert cls == PromptInjectionSuite

    def test_get_suite_invalid(self) -> None:
        with pytest.raises(KeyError):
            get_suite("nonexistent")

    def test_suite_is_base_suite(self) -> None:
        for name, cls in SUITE_REGISTRY.items():
            assert issubclass(cls, BaseSuite)


class TestPromptInjectionSuite:
    def test_generate_cases(self) -> None:
        suite = PromptInjectionSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_build_suite(self) -> None:
        suite = PromptInjectionSuite()
        benchmark_suite = suite.build_suite()
        assert benchmark_suite.name == "prompt_injection"
        assert len(benchmark_suite.test_cases) >= 8
        for tc in benchmark_suite.test_cases:
            assert tc.category == "prompt_injection"


class TestToolPoisoningSuite:
    def test_generate_cases(self) -> None:
        suite = ToolPoisoningSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_build_suite(self) -> None:
        suite = ToolPoisoningSuite()
        benchmark_suite = suite.build_suite()
        assert benchmark_suite.category == "tool_poisoning"


class TestSSRFSuite:
    def test_generate_cases(self) -> None:
        suite = SSRFSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_ids_have_ssrf_prefix(self) -> None:
        suite = SSRFSuite()
        cases = suite.generate_cases()
        for tc in cases:
            assert tc.id.startswith("ssrf-")


class TestDataExfiltrationSuite:
    def test_generate_cases(self) -> None:
        suite = DataExfiltrationSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_build_suite(self) -> None:
        suite = DataExfiltrationSuite()
        benchmark_suite = suite.build_suite()
        assert benchmark_suite.description != ""


class TestJailbreakSuite:
    def test_generate_cases(self) -> None:
        suite = JailbreakSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_severity_distribution(self) -> None:
        suite = JailbreakSuite()
        cases = suite.generate_cases()
        severities = {tc.severity.value for tc in cases}
        assert "high" in severities or "critical" in severities


class TestMemoryAttackSuite:
    def test_generate_cases(self) -> None:
        suite = MemoryAttackSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_ids_have_ma_prefix(self) -> None:
        suite = MemoryAttackSuite()
        cases = suite.generate_cases()
        for tc in cases:
            assert tc.id.startswith("ma-")


class TestMultiAgentSuite:
    def test_generate_cases(self) -> None:
        suite = MultiAgentSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8

    def test_weight_range(self) -> None:
        suite = MultiAgentSuite()
        cases = suite.generate_cases()
        for tc in cases:
            assert 0.5 <= tc.weight <= 2.0


class TestAllSuitesConsistency:
    def test_all_suites_have_cases(self) -> None:
        for name, cls in SUITE_REGISTRY.items():
            suite = cls()
            cases = suite.generate_cases()
            assert len(cases) > 0, f"Suite {name} has no test cases"

    def test_all_suites_have_unique_ids(self) -> None:
        for name, cls in SUITE_REGISTRY.items():
            suite = cls()
            cases = suite.generate_cases()
            ids = [tc.id for tc in cases]
            assert len(ids) == len(set(ids)), f"Suite {name} has duplicate IDs"

    def test_all_suites_have_required_fields(self) -> None:
        for name, cls in SUITE_REGISTRY.items():
            suite = cls()
            assert suite.name, f"Suite {name} has no name"
            assert suite.category, f"Suite {name} has no category"
            assert suite.description, f"Suite {name} has no description"
