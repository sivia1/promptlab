.PHONY: install install-dev lint format typecheck test serve run demo ui clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy

test:
	pytest --cov=promptlab --cov-report=term-missing

# Run the API backend.
serve:
	promptlab serve

# Quick terminal smoke test of the full pipeline (offline stub if no key).
run:
	promptlab run -q "How do I reset my password?" \
		-p "You are a helpful assistant. Answer clearly." \
		-p "Answer briefly." \
		-p "Think step by step, then answer." \
		-m llama-3.3-70b-versatile

# Frontend dev server (Vite).
ui:
	cd frontend && npm install && npm run dev

clean:
	rm -rf promptlab.db experiments/*.json exports/*.json exports/*.csv \
		.pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
