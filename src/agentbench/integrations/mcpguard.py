"""MCPGuard policy generation from AgentBench benchmark results."""

from __future__ import annotations

from pathlib import Path

import yaml

from agentbench.models import ScoreReport, TestStatus


class MCPGuardPolicyGenerator:
    """Generates MCPGuard-compatible YAML policies from benchmark results.

    Maps failed benchmark tests to MCPGuard policy rules (allow/deny lists,
    blocking flags).
    """

    CATEGORY_TO_BLOCK_FLAG = {
        "prompt_injection": "block_on_injection",
        "tool_poisoning": "block_on_poisoning",
        "ssrf": "block_on_resource_scan",
        "jailbreak": "block_on_injection",
        "data_exfiltration": "block_on_injection",
        "memory_attacks": "block_on_injection",
        "multi_agent": "block_on_injection",
    }

    CATEGORY_TO_TOOL_PATTERNS = {
        "tool_poisoning": ["exec", "shell", "bash", "sudo", "delete_", "drop_", "admin_"],
        "ssrf": ["fetch_url", "request", "http_", "curl", "wget"],
        "data_exfiltration": ["send_email", "upload", "exfil", "write_file"],
    }

    def generate(self, report: ScoreReport) -> dict:
        """Generate an MCPGuard policy dict from a benchmark report.

        Args:
            report: Score report from a benchmark run.

        Returns:
            MCPGuard-compatible policy dictionary.
        """
        policy: dict = {
            "mode": "http",
            "listen_host": "127.0.0.1",
            "listen_port": 8080,
            "target_url": report.config.get("target", "http://localhost:8000"),
            "rate_limit": 100,
            "rate_window": 60,
            "allow": ["get_", "read_", "search_", "list_"],
            "deny": [],
            "block_on_injection": False,
            "block_on_poisoning": False,
            "block_on_resource_scan": False,
            "block_on_prompt_scan": False,
            "log_dir": "./mcpguard_logs",
        }

        failed_tests = [r for r in report.results if r.status == TestStatus.FAILED]
        failed_categories = {r.test_case.category for r in failed_tests}

        for category in failed_categories:
            flag = self.CATEGORY_TO_BLOCK_FLAG.get(category)
            if flag:
                policy[flag] = True

            patterns = self.CATEGORY_TO_TOOL_PATTERNS.get(category, [])
            for pattern in patterns:
                if pattern not in policy["deny"]:
                    policy["deny"].append(pattern)

        if report.overall_score < 50:
            policy["rate_limit"] = max(policy["rate_limit"], 20)

        return policy

    def save_yaml(self, report: ScoreReport, filepath: str | Path) -> str:
        """Save an MCPGuard policy as a YAML file.

        Args:
            report: Score report from a benchmark run.
            filepath: Output YAML file path.

        Returns:
            Path to the saved file.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        policy = self.generate(report)
        with open(path, "w") as f:
            yaml.dump(policy, f, default_flow_style=False, sort_keys=False, Dumper=yaml.SafeDumper)
        return str(path)
