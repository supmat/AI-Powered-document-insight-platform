.PHONY: local-run local-stop setup format pre-commit test env-check

env-check: ## Verify .env exists and contains all required keys
	@if [ ! -f .env ]; then \
		echo ""; \
		echo "⚠️  No .env file found! Creating one from .env.example..."; \
		cp .env.example .env; \
		echo "✅ .env created. Please open it and fill in the required values:"; \
		echo "   • POSTGRES_PASSWORD"; \
		echo "   • MINIO_ROOT_PASSWORD"; \
		echo "   • RABBITMQ_PASSWORD"; \
		echo "   • SECRET_KEY  (run: openssl rand -hex 32)"; \
		echo "   • GEMINI_API_KEY  (optional, enables cloud AI)"; \
		echo ""; \
		exit 1; \
	fi
	@MISSING=""; \
	for key in POSTGRES_PASSWORD MINIO_ROOT_PASSWORD RABBITMQ_PASSWORD SECRET_KEY; do \
		val=$$(grep "^$$key=" .env | cut -d'=' -f2 | tr -d ' '); \
		if [ -z "$$val" ]; then MISSING="$$MISSING $$key"; fi; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo ""; \
		echo "❌ ERROR: The following required keys are empty in your .env file:"; \
		for k in $$MISSING; do echo "   • $$k"; done; \
		echo ""; \
		echo "Please open .env and fill in these values before running."; \
		echo "Tip: generate SECRET_KEY with:  openssl rand -hex 32"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ .env looks good!"

local-run: env-check ## Start all dependent infrastructure and development servers locally
	@echo "Starting up the whole stack via Docker Compose..."
	sudo docker compose up -d --build
	@echo "Starting Gateway and Processing Worker in parallel. Press Ctrl+C to stop."
	@trap 'kill 0' SIGINT; \
	.venv/bin/uvicorn gateway.main:app --reload --port 8001 & \
	.venv/bin/python -m processing.main & \
	wait

gateway-run: ## Start the FastAPI gateway server locally
	.venv/bin/uvicorn gateway.main:app --reload --port 8001

worker-run: ## Start the background processing worker to listen to RabbitMQ
	.venv/bin/python -m processing.main

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
