# AgentBench

[![CI](https://github.com/Carlos-Projects/agentbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Carlos-Projects/agentbench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen.svg)](https://github.com/Carlos-Projects/agentbench/actions)

Automated benchmarking framework for evaluating AI agent security.

AgentBench executes standardized test suites against AI agents, generates
comparable security scores, and produces reproducible security reports.
Complementary to [mcpwn](https://github.com/Carlos-Projects/mcpwn) (active
attacks), AgentBench focuses on standardized, repeatable benchmarking.

## Features

- **8 Benchmark Suites**: Prompt injection, tool poisoning, SSRF, data
  exfiltration, jailbreak, memory attacks, multi-agent attacks, MCP attacks
- **Automated Scoring**: Normalized 0-100 scores per category and overall
- **Comparative Analysis**: Compare agents, versions, and configurations
- **Trend Analysis**: Track security posture over time
- **Leaderboards**: Generate ranked leaderboards from benchmark results
- **Multiple Report Formats**: Console (Rich), JSON, HTML, Markdown
- **CI/CD Ready**: GitHub Actions integration for regression testing
- **Reproducible**: Fixed seeds and controlled test environments

## Installation

```bash
git clone https://github.com/Carlos-Projects/agentbench.git
cd agentbench
pip install -e .
```

For development (includes test/lint dependencies):

```bash
pip install -e ".[dev]"
```

## Quick Start

Run all benchmark suites against a target agent:

```bash
agentbench run http://localhost:8080 --agent-id my-agent
```

Run specific suites:

```bash
agentbench run http://localhost:8080 --suites prompt_injection,ssrf
```

Save reports:

```bash
agentbench run http://localhost:8080 --output results.json --html report.html
```

### Example Output

```bash
$ agentbench info
AgentBench v0.2.0-dev
  Python: 3.13.9 | Platform: macOS-arm64

Suites: 8 built-in (64 test cases)
  prompt_injection   → 8 tests
  tool_poisoning     → 8 tests
  ssrf               → 8 tests
  data_exfiltration  → 8 tests
  jailbreak          → 8 tests
  memory_attacks     → 8 tests
  multi_agent        → 8 tests
  mcp_attack         → 8 tests

Output formats: console, JSON, HTML, Markdown, SARIF, MCPGuard, MCPscop
API formats: generic, openai, anthropic, mcp
```

```bash
$ agentbench suite --list
Available Benchmark Suites:
  prompt_injection    Tests agent resistance to prompt injection attacks
  tool_poisoning      Tests agent resistance to tool poisoning
  ssrf                Tests agent resistance to SSRF attacks
  data_exfiltration   Tests agent resistance to data exfiltration
  jailbreak           Tests agent resistance to jailbreak techniques
  memory_attacks      Tests agent resistance to memory poisoning
  multi_agent         Tests agent security in multi-agent scenarios
  mcp_attack          Tests MCP protocol-level security
```

## Commands

### `agentbench run`

Execute benchmark suites against a target agent.

```bash
agentbench run <TARGET_URL> [options]
```

Options:
- `--suites, -s`: Comma-separated suite names or `all` (default)
- `--agent-id, -a`: Agent identifier
- `--agent-version, -v`: Agent version string
- `--output, -o`: JSON output file
- `--html`: HTML report output
- `--markdown, -m`: Markdown report output
- `--timeout, -t`: Request timeout in seconds (default: 30)
- `--header, -H`: Additional HTTP headers

### `agentbench suite`

List and inspect benchmark suites.

```bash
agentbench suite --list
agentbench suite --show prompt_injection
```

### `agentbench compare`

Compare two benchmark reports.

```bash
agentbench compare baseline.json target.json
```

### `agentbench leaderboard`

Generate a leaderboard from multiple reports.

```bash
agentbench leaderboard report1.json report2.json report3.json
```

### `agentbench report`

Convert reports between formats.

```bash
agentbench report results.json --html report.html --markdown report.md
```

### `agentbench trend`

Analyze security trends over time.

```bash
agentbench trend v1.json v2.json v3.json
```

## Benchmark Suites

| Suite | Category | Description | Tests |
|-------|----------|-------------|-------|
| `prompt_injection` | Prompt Injection | Direct, indirect, role-playing, multi-language, code-context, nested, delimiter, JSON injection | 8 |
| `tool_poisoning` | Tool Poisoning | Argument injection, name confusion, permissions, output manipulation, chaining, overflow, discovery, type confusion | 8 |
| `ssrf` | SSRF | Internal IP, localhost, metadata, DNS rebinding, URL scheme, redirect, IPv6, port scanning | 8 |
| `data_exfiltration` | Data Exfiltration | Secret extraction, encoding, files, gradual, steganography, session, training data, error leaks | 8 |
| `jailbreak` | Jailbreak | Hypothetical, research, Base64, translation, decomposition, emotional, smuggling, awareness | 8 |
| `memory_attacks` | Memory Attacks | Poisoning, overflow, false memory, leak, context, history, tokens, persona | 8 |
| `multi_agent` | Multi-Agent | Inter-agent injection, cooperation, impersonation, consensus, delegation, cascade, coordinated, resources | 8 |
| `mcp_attack` | MCP Attack | Tool enumeration, argument injection, protocol downgrade, malformed JSON-RPC, resource access, prompt injection via tool response, notification flooding, ping/pong manipulation | 8 |

## Scoring

Scores are normalized to a 0-100 scale:
- **90-100**: Excellent security posture
- **70-89**: Good security with minor gaps
- **50-69**: Moderate security, improvements needed
- **0-49**: Poor security, significant vulnerabilities

## Integration

AgentBench integrates with the MCP security ecosystem:

- **[mcpwn](https://github.com/Carlos-Projects/mcpwn)**: Active attack
  framework (complementary: mcpwn attacks, AgentBench benchmarks)
- **[MCPGuard](https://github.com/Carlos-Projects/mcpguard)**: Runtime
  security proxy (AgentBench generates compatible policies)
- **[MCPscop](https://github.com/Carlos-Projects/mcpscope)**: Security
  dashboard (consumes AgentBench reports)
- **[mcp-taxonomy](https://github.com/Carlos-Projects/mcp-taxonomy)**: Shared
  security classification taxonomy

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/agentbench/

# Coverage
coverage run -m pytest tests/ -v
coverage report
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policies and disclosure.

## License

MIT License - see [LICENSE](LICENSE).
