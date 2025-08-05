# Test automation for ezib_async
# Usage: make -f Makefile <target>

.PHONY: help test-unit test-integration test-all test-fast test-coverage clean-test

help:
	@echo "Available test targets:"
	@echo "  test-unit        Run unit tests only (fast, no external dependencies)"
	@echo "  test-integration Run integration tests (requires IB Gateway/TWS)"
	@echo "  test-all         Run all tests"
	@echo "  test-fast        Run unit tests with minimal output"
	@echo "  test-coverage    Run unit tests with coverage report and update badges"
	@echo "  clean-test       Clean test artifacts"

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -m "not integration" -v --tb=short

test-integration:
	@echo "Running integration tests (requires IB Gateway/TWS)..."
	pytest tests/ -m integration --run-integration -v --tb=short

test-all:
	@echo "Running all tests..."
	pytest tests/ --run-integration -v --tb=short

test-fast:
	@echo "Running unit tests (fast mode)..."
	pytest tests/ -m "not integration" -q --tb=line

test-coverage:
	@echo "Running unit tests with coverage..."
	pytest tests/ -m "not integration" --cov=src/ezib_async --cov-report=html --cov-report=term-missing --cov-report=json
	@echo "Updating coverage badges..."
	python scripts/update_badges.py

test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch tests/ -m "not integration" -- -v --tb=short

clean-test:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# CI targets
ci-unit:
	pytest tests/ -m "not integration" --tb=short --strict-markers

ci-integration:
	pytest tests/ -m integration --run-integration --tb=short --strict-markers