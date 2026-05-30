# Contributing to AgentBench

👋 **Welcome, and thank you for your interest in AgentBench!**

We're building an automated benchmarking framework for AI agent security — and we need you. Whether you're fixing a bug, adding a benchmark suite, improving documentation, or just offering feedback, every contribution makes this project stronger.

## First Time Contributor?

Never contributed to AgentBench before? That's okay!

- Check out issues tagged `good first issue`
- Try running the existing benchmark suites and reporting edge cases
- Add a new test for an existing suite
- Improve the documentation or add a code comment where something was confusing

We're here to help you succeed. Don't hesitate to ask for guidance.

## Need Help?

Questions or feedback?

- Open a [GitHub Issue](https://github.com/Carlos-Projects/agentbench/issues)
- Check if someone else had the same question first
- Be descriptive: include your environment, what you tried, and what happened

## Development Setup

```bash
git clone https://github.com/Carlos-Projects/agentbench.git
cd agentbench
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Style

- Type hints are required for all public functions
- Follow PEP 8 (enforced by ruff)
- Use descriptive names and docstrings for public APIs
- Keep functions focused and single-purpose

## Testing

- All new features must include tests
- Minimum test coverage: 80%
- Run tests before submitting:

```bash
python -m pytest tests/ -v
coverage run -m pytest tests/ -v
coverage report
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run linting and tests (`ruff check . && python -m pytest`)
5. Commit with descriptive message
6. Push to your fork and open a PR

## Adding a Benchmark Suite

1. Create a new file in `src/agentbench/suites/`
2. Extend `BaseSuite` and implement `generate_cases()`
3. Register in `src/agentbench/suites/__init__.py` `SUITE_REGISTRY`
4. Add tests in `tests/test_suites/`

## Security

Found a vulnerability? See [SECURITY.md](SECURITY.md).

---

💡 This project is governed by a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold its principles.
