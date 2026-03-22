.PHONY: local-run local-stop setup format pre-commit test

local-run: ## Start all dependent infrastructure and development servers locally
	@echo "Starting up the whole stack via Docker Compose..."
	sudo docker compose up -d --build

local-stop: ## Spin down all infrastructure components
	@echo "Stopping Docker Compose stack..."
	sudo docker compose down

setup: ## Install local python dependencies and pre-commit hooks
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pre-commit install

format: ## Run the code formatters manually over all code
	.venv/bin/black .
	.venv/bin/ruff check . --fix

test: ## Run the pytest suite
	.venv/bin/pytest

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
