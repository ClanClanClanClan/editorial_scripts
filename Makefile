.PHONY: install hooks lint fix test security secrets ci clean

install:
	poetry install

hooks:
	poetry run pre-commit install

lint:
	poetry run ruff check tests
	poetry run black --check tests

fix:
	poetry run ruff check tests --fix
	poetry run black tests

test:
	poetry run pytest

security:
	mkdir -p artifacts/security
	poetry run bandit -q -r production/src -x tests,dev,archive -f json -o artifacts/security/bandit.json || true
	poetry run pip-audit -s -f json -o artifacts/security/pip-audit.json || true

secrets:
	poetry run detect-secrets-hook --baseline .secrets.baseline $(shell git ls-files)

ci:
	$(MAKE) lint
	$(MAKE) test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov artifacts/security
