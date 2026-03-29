AI-Powered Document Insight Platform

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

## Quick Start (Local Development)

### Prerequisites
*   Docker & Docker Compose
*   Python 3.10+
*   `make` utility

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
