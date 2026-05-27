# Changelog

## [0.2.0-dev] - 2026-05-26

### Added
- 8 benchmark suites (64 tests): prompt injection, tool poisoning, SSRF, data exfiltration, jailbreak, memory attacks, multi-agent, MCP attack
- Severity-weighted scoring engine
- Comparative analysis, trend analysis with NumPy linear regression
- 6 report formats: console (Rich), JSON, HTML (Plotly), Markdown, SARIF v2.1.0, MCPGuard/MCPscop
- SQLite persistence, parallel execution, retry with exponential backoff
- Plugin system for external suites
- Anthropic/OpenAI/MCP API format support
- Webhook notifications, CI/CD integration, Docker, Sphinx docs
- Security audit: 22 findings fixed
- 299 tests, 46 source files, 86% coverage

## [0.1.0] - 2026-05-26

### Added
- Initial release of AgentBench - core benchmarking framework
- 7 benchmark suites: prompt injection, tool poisoning, SSRF, data exfiltration, jailbreak, memory attacks, multi-agent
- Scoring engine with weighted metrics and score normalization
- Comparative analysis between agent versions
- Trend analysis with moving averages and score prediction
- Leaderboard generation and publishing (JSON, Markdown)
- Multiple report formats: console (Rich), JSON, HTML (Jinja2), Markdown
- CLI with 6 commands: run, suite, compare, leaderboard, report, trend
- CI/CD pipelines for GitHub Actions (test + publish)
- MCP and OpenAI-compatible target support
- 163 tests with 96% code coverage
