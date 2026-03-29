# AI-Powered Document Insight Platform [![CI](https://github.com/supmat/AI-Powered-document-insight-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/supmat/AI-Powered-document-insight-platform/actions/workflows/ci.yml)

An enterprise-grade document ingestion and Insight platform powered by the Retrieval-Augmented Generation (RAG) architecture. This system allows tenants to securely upload documents, extract structured text and entities using Machine Learning pipelines, generate vector embeddings, and query them naturally using Large Language Models (LLMs) like Google Gemini.

*   **Multi-Tenant Architecture**: Strict data isolation using row-level security concepts.
*   **Asynchronous Processing Pipeline**: Non-blocking ingestion via FastAPI, RabbitMQ, and background Python workers.
*   **Vector Search Engine**: High-performance semantic retrieval using PostgreSQL (`pgvector`).
*   **Hybrid RAG Approach**: Direct integration with Google Gemini 2.0 SDK for answers, with a local open-source CPU model fallback (TinyLlama) for robustness.
*   **Intelligent Text Extraction**: Handles native PDFs (via `PyMuPDF`) and images (via `EasyOCR` / `Gemini Vision`).
*   **Named Entity Recognition (NER)**: Identifies and tags key identifiers (People, Orgs, custom UUIDs/Codes) using `spaCy`.

## Documentation

Detailed documentation on how to interact with the backend services can be found here:

* **[API Reference Documentation](docs/api_reference.md)**: A complete guide for Frontend Developers, including authentication steps, document management endpoints, and querying procedures.
* **[Onboarding Guide](docs/onboarding.md)**: A deep-dive into the system architecture, technology stack, and local development setup for new contributors.

## Quick Start (Local Development)

### Prerequisites
*   **Operating System**:
    *   **Linux / macOS**: Fully supported natively.
    *   **Windows**: Supported via **WSL2** (Windows Subsystem for Linux). Running directly in PowerShell/CMD is not supported due to `Makefile` dependencies.
*   **Docker & Docker Compose** (Desktop or Engine)
*   **Python 3.10+**
*   **`make` utility** (Build automation)

### Environment Setup

1.  Copy the environment template:
    ```bash
    cp .env.example .env
    ```
2.  Fill in the `.env` variables (specifically your `GEMINI_API_KEY`).
3.  Set up the Python virtual environment:
    ```bash
    make install
    ```

### Running the Stack

To build and run the entire infrastructure (PostgreSQL, RabbitMQ, MinIO, FastAPI Gateway, and Processing Worker), run:

```bash
make local-run
```

To run the automated E2E curl smoke test (the stack must be running):
```bash
make e2e-curl
```

To clean up cache and perform a hard restart:
```bash
make restart
```

To stop the background containers:
```bash
make local-stop
```

To perform a "factory reset" (wipe all databases, object storage, and local Docker images):
```bash
make deep-clean
```

### Observability

Metrics and distributed traces are collected via OpenTelemetry. You can view them using the following live links (when the telemetry stack is running locally):
- **Metrics (Prometheus):** [http://localhost:9090](http://localhost:9090)
- **Traces (Jaeger):** [http://localhost:16686](http://localhost:16686)

## Developer Workflow & CI/CD

This project uses **GitHub Actions** to automate quality assurance and deployments.

*   **On Commit (Pull Requests):** When you push code or open a Pull Request, the CI pipeline runs a fast, core suite of checks. This includes `pre-commit` hooks (formatting, linting with Ruff, and type-checking with MyPy) and standard unit tests to ensure your changes are safe and functional.
*   **On Merge (Push to Main):** When a Pull Request is successfully merged into the `master`/`main` branch, a broader scope of actions is triggered. This includes running the full, comprehensive test suite (including E2E and integration tests), rebuilding the production-ready Docker images, and publishing them to the container registry.
