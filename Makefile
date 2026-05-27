.PHONY: test test-cov lint typecheck build clean all

test:
	python -m pytest tests/ -v

test-cov:
	coverage run -m pytest tests/ -v && coverage report

lint:
	ruff check src/ tests/

typecheck:
	mypy src/agentbench/ --ignore-missing-imports

build:
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage

all: lint typecheck test-cov
