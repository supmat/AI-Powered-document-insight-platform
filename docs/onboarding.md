# Onboarding Guide: AI-Powered Document Insight Platform

Welcome to the **Document Insight Platform**!

This completely asynchronous, distributed RAG (Retrieval-Augmented Generation) system allows enterprise tenants to upload complex documents (PDFs, Images), have them processed through advanced machine learning pipelines (OCR, NER, Vectorization), and query them naturally using Large Language Models.

This document serves as your technical map to understanding the "Why" and "How" of our entire stack.

---

## 1. High-Level Architecture Overview

Our system is broken down into two heavily decoupled microservices communicating over a message broker. This prevents the heavy machine-learning processing from blocking our lightning-fast HTTP API response times.

### The Core Services:
1. **Gateway (Backend-For-Frontend)**: A FastAPI application that serves as the entry point. It handles authentication, rate-limiting, synchronous RAG queries, and fast file uploads directly to Object Storage.
2. **Processing Worker**: A headless Python daemon. It listens to RabbitMQ, downloads files, extracts text, runs Named Entity Recognition (`spaCy`), generates 768-D vector embeddings, and saves them to the PostgreSQL database.

### The Infrastructure Layer:
- **Traefik (Edge Reverse Proxy)**: Fronts the Gateway, handling incoming HTTPS traffic, automatic SSL certificate provisioning, and load balancing. It ensures external requests are strictly secure before they reach the backend APIs.
- **PostgreSQL (`pgvector`)**: Our single source of truth for both relational user/tenant data AND semantic vector embeddings.
- **RabbitMQ**: The message broker prioritizing and routing document processing tasks asynchronously.
- **MinIO**: S3-compatible object storage where raw user uploads (PDFs, images) are securely stored before and after processing.
- **Observability Stack (System Metrics & Tracing)**: We use **Prometheus** to scrape real-time RED metrics (Rate, Error, Duration) from FastAPI, **Jaeger** for distributed tracing across the Gateway and Worker via OpenTelemetry, and **Grafana** to visualize these metrics in interactive dashboards.

### 🔒 Data Security & Encryption
- **In-Transit**: All external frontend-to-API communication is fully encrypted using TLS at the Traefik edge layer to protect Bearer tokens.
- **At-Rest**: Documents are stored in MinIO volumes, and vector embeddings in PostgreSQL. User passwords are mathematically one-way hashed using `bcrypt` via `passlib` before ever touching the database logic.

---

## 2. Technology Stack Breakdown (The "Why")

We chose these specific technologies to maximize performance, developer velocity, and deployment resilience:

### FastAPI (Gateway & API)
* **Why**: It is built on modern asynchronous Python (`asyncio`), making it phenomenally fast for highly concurrent I/O operations (like database reads or API calls). It natively integrates with Pydantic, giving us strict, self-documenting type validation on everything entering the system.

### PostgreSQL + `pgvector`
* **Why**: Instead of managing a dedicated Vector Database (like Pinecone) *alongside* a relational database for users, we combined them. `pgvector` allows us to perform lightning-fast nearest-neighbor searches (Cosine Similarity) directly in SQL, while natively enforcing row-level multi-tenancy (`WHERE tenant_id = X`).

### RabbitMQ (Message Broker)
* **Why**: Machine Learning (OCR, extracting embeddings) takes time. If the Gateway waited for a 50-page PDF to process, the HTTP connection would timeout. RabbitMQ ensures the Gateway can instantly respond with a `202 Accepted` while background Workers safely chew through the queue at their own pace.

### Hybrid ML Strategy (The "Fallback" Architecture)
Our system is designed to gracefully degrade if the cloud fails:
* **LLM Engine**: Primary route is the **Google Gemini API** (ultra-fast, massive context). Fallback is a local HuggingFace CPU model (`TinyLlama`).
* **Embeddings**: Primary is `text-embedding-004`. Fallback is local Sentence Transformers (`all-mpnet-base-v2`). Crucially, both strictly generate exactly **768-dimensional** vectors, ensuring DB schema compatibility.
* *Detailed Read: [ADR 004: Extraction Pipeline](./adr/004-document-extraction-and-nlp-pipeline.md)*

### Traefik (Edge Router & Reverse Proxy)
* **What it Does**: Traefik acts as the single "front door" for the entire platform. Instead of exposing every Docker container directly to the host machine, Traefik binds to ports 80 and 443 and routes traffic internally based on explicit rules.
* **Configuration Mechanics**:
  - **Static Config (`traefik.yml`)**: Defines the global entry points (Ports 80/443) and enforces mandatory redirection from HTTP to HTTPS.
  - **Dynamic Config (`dynamic_conf.yml`)**: Declares the actual routing logic. It maps traffic based on URL patterns:
    - `PathPrefix(/api)` → Routes to the FastAPI `gateway`.
    - `Host(jaeger.localhost)` → Routes to the distributed tracing UI.
    - `Host(grafana.localhost)` → Routes to the observability dashboards.
* **Local TLS**: We use custom OpenSSL certificates to perform local TLS termination at the edge, guaranteeing that all testing explicitly mimics secure production environments.

---

## 3. Gateway Architecture & Flow

The **Gateway** is the synchronous FastAPI web server that acts as our Backend-For-Frontend (BFF). It is designed to be highly concurrent, validating incoming traffic and routing it rapidly without ever performing heavy machine-learning lifting itself.

### Key Components inside `gateway/`
1. **`main.py` (The Entrypoint)**: Sets up the FastAPI application framework. It dynamically registers all route modules (`auth`, `ingestion`, `query`), and configures global middleware (CORS, Rate Limiting, OpenTelemetry). It also manages the async startup lifecycle (e.g., ensuring PostgreSQL database tables and MinIO root buckets exist before opening port 8001 to Traefik).
2. **`api/` (Routing & Endpoints)**: Contains isolated modules for different controller domains.
   - `auth.py`: Validates credentials, securely hashes passwords, and issues stateless JWT access tokens.
   - `ingestion.py`: Handles HTTP multipart streaming of `UploadFile` payloads directly over to raw MinIO storage.
   - `documents.py`: Exposes endpoints for users to list or delete their vectorized context, strictly protected via `tenant_id` ownership checks.
3. **`core/` (Security & Middleware)**: Houses `security.py` for token verification algorithms (HS256 encryption against a local secret) and `rate_limit.py`, which leverages an IP-based sliding window algorithm to immediately reject abusive traffic spikes with an HTTP 429 response.
4. **`models/` (Pydantic Schemas)**: Strict Python data classes defining exactly what JSON configurations are allowed into and out of the API. This guarantees 100% type safety, prevents injection attacks, and automatically generates interactive Swagger documentation.
5. **`services/` (External Adapters)**: Contains stateless clients for external infrastructure (e.g., `minio_client.py`, `rabbitmq_client.py`). Most crucially, the Gateway acts strictly as a **Publisher** to RabbitMQ. When a document arrives, the Gateway streams the raw bytes to MinIO and blindly triggers `publish_document_event()` to drop a job on the queue.

### Connection Lifecycle (How a Request is Handled)
1. **Edge Entry**: Traefik receives the HTTPS request, mathematically decrypts the TLS certificate, and load-balances the raw HTTP packet directly to the Gateway container on port 8001.
2. **Middleware Chain**: The request immediately hits `main.py` middleware injections. CORS checks verify permitted Origins (`localhost:3000`), the Rate Limiter deducts a token from the client's IP bucket, and the OpenTelemetry Tracer begins logging request duration.
3. **Authentication Boundary**: If the specific route is protected (e.g., `/api/v1/query`), FastAPI `Depends(get_current_user)` intercepts the request to validate the Bearer JWT, extracting the `user_email` to form a trusted `current_user` context object.
4. **Controller Actions**: The designated API route operates safely assuming perfect auth context. It validates incoming request bodies dynamically against Pydantic constraint sets.
5. **Infrastructure Exit**: The Gateway either synchronously executes SQLAlchemy bounds to query `pgvector`, or acts asynchronously, acknowledging a file upload via a HTTP `202 Accepted` while backgrounding an event over to RabbitMQ for processing via the Worker.

---

## 4. Codebase Structure (Where to find things)

The repository is modularized by technical domain:

```bash
.
├── gateway/         # The FastAPI Web Server
│   ├── api/         # HTTP Routes (Auth, Ingestion, Documents)
│   ├── core/        # Security, Config, JWT, Rate Limiting
│   ├── models/      # Pydantic Schemas
│   └── services/    # External clients (MinIO, RabbitMQ publisher)
│
├── processing/      # The Asynchronous Background Worker
│   ├── services/    # Heavy ML logic (spaCy NER, PDF Extraction)
│   └── main.py      # The RabbitMQ Consumer Loop
│
├── query/           # The specialized RAG retrieval logic (Used by Gateway)
│   └── services/    # Gemini API clients, Vector similarity search
│
├── shared/          # Code shared by BOTH Gateway & Worker
│   ├── database.py  # SQLAlchemy async engine initialization
│   └── models.py    # Core DB Tables (Users, DocumentChunks)
│
├── k8s/             # Kubernetes Deployment Manifests
├── docker-compose.yml # The core local infrastructure map
└── Makefile         # The central command runner (make local-run)
```

---

## 5. Containerization & Production (Docker/K8s)

### Docker Build Strategy (The Monorepo Approach)
The platform compiles into two separate lightweight Docker images (`gateway` and `worker`) housed under a single git monorepo. Both services critically depend on the data structures inside the `shared/` directory (SQLAlchemy schemas and database connectors).
* **Root Build Context**: In `docker-compose.yml`, the build context for both images is explicitly set to the project root (`.`). This design pattern allows the independent `gateway/Dockerfile` and `processing/Dockerfile` to safely `COPY shared/ ./shared/` into their respective containers at build time.
* **Layer Caching Optimization**: Both Dockerfiles strictly copy and install `requirements.txt` *before* moving the Python source code. This leverages Docker's layer cache, meaning source modifications don't brutally trigger a 5-minute `pip install` loop.
* **ML Asset Precaching**: The worker depends intensely on heavy Natural Language Processing. The `processing/Dockerfile` manually executes `python -m spacy download en_core_web_sm`. By baking these Neural Network weights statically into a locked image layer, it eliminates startup latency/network dependencies in stateless production clusters.

### Kubernetes Orchestration (`k8s/`)
While `docker-compose.yml` ties these containers together for rapid local testing, production scaling relies identically on distributed Kubernetes. The `k8s/` directory translates our local stack into declarative cloud resources:
* **`namespace.yaml`**: Carves out a logical boundary (`document-insight`) to isolate our platform's CPU/RAM/Network allocations.
* **`config-secrets.yaml`**: Abstractly injects configuration (mapping our `.env` methodology to native K8s ConfigMaps and securely encrypted Secrets).
* **`persistence.yaml` & `postgres.yaml`**: Controls StatefulSets and PersistentVolumeClaims natively. It guarantees that multi-gigabyte MinIO document blobs and `pgvector` Postgres embeddings survive pod restarts and hardware failures.
* **`infra.yaml`**: Deploys RabbitMQ brokers and MinIO seamlessly.
* **`apps.yaml`**: Governs the stateless `Gateway` API and `Processing Worker` Deployments. This explicitly defines how we horizontally autoscale background ML workers independently from web traffic.

---

## 6. Local Environment Setup

We prioritize identical Dev/Prod environments. To achieve this, your local setup will run entirely within Docker Compose.

### Prerequisites
1. Docker & Docker Compose plugin installed.
2. Python 3.10+ (for local IDE autocompletion/linting).
3. `make` utility.

### Step-by-Step Initialization

**1. Copy the Configuration**
We use a `.env` file to manage secrets. Copy the example template:
```bash
cp .env.example .env
```
*Open `.env` and fill in your `GEMINI_API_KEY`. Without it, the system will fall back to local CPU models, which are significantly slower and less accurate.*

**2. Setup Local Virtual Environment (For IDE Intelligence)**
This installs the pip requirements and sets up `pre-commit` hooks for automatic Black/Ruff formatting on git commit.
```bash
make setup
```

**3. Boot the Matrix**
This single command builds the Gateway and Worker Docker images, spins up Postgres, MinIO, and RabbitMQ, automatically creates the DB tables, and tails the logs.
```bash
make local-run
```
*The API is now live at: `http://localhost:8001/docs`*

---

## 7. The Critical Path Data Flows

To understand how to modify the system, understand these two flows perfectly:

### Flow A: Ingestion (How Data Gets In)
1. **[Gateway]** Client POSTs a PDF to `/api/v1/upload_documents/`.
2. **[Gateway]** Authenticates user, validates file extension/size.
3. **[Gateway]** Streams the raw bytes directly to MinIO.
4. **[Gateway]** Pushes a JSON payload `{"document_id": "X", "file_path": "Y"}` to the RabbitMQ queue.
5. **[Gateway]** Immediately returns a `202 Accepted` to the client.
6. **[Worker]** Dequeues the RabbitMQ message.
7. **[Worker]** Downloads the file from MinIO.
8. **[Worker]** Runs `PyMuPDF` (or `EasyOCR`) to rip the raw text.
9. **[Worker]** Slices the text into chunks and runs `spaCy` NER over them.
10. **[Worker]** Sends the chunks to Gemini to get 768-D Vector Embeddings.
11. **[Worker]** Writes the Chunks, Entities, and Embeddings into the PostgreSQL `document_chunks` table.

### Flow B: RAG Querying (How Data is Used)
1. **[Gateway]** Client POSTs a question to `/api/v1/query/`.
2. **[Gateway]** Validates JWT and extracts the `tenant_id` (Crucial for security!).
3. **[Gateway -> Query Module]** Sends the user's question to the Gemini API to convert it into a 768-D Vector.
4. **[Query Module]** Executes an Async SQLAlchemy query against Postgres `pgvector` ordering by `<=>` (Cosine Distance) to find the `top_k` most similar chunks of text... **WHERE `tenant_id` matches**. The `top_k` parameter (default: 5) dictates exactly how many semantic text snippets are sent to the LLM. A larger `top_k` provides more context but consumes more tokens and latency.
5. **[Query Module]** Takes those `top_k` retrieved text chunks and injects them into a strict prompt template alongside the user's original question.
6. **[Query Module]** Asks Gemini to answer the question using *only* the provided context.
7. **[Gateway]** Returns the synthetic answer, citation quotes, and extracted entities to the user.

---

## 8. Testing & CI/CD Expectations

We treat the `master` branch as sacred. The testing strategy relies on robust mocking for external components, ensuring unit tests run fast and deterministically.

### Local Testing
1. **Pre-commit Hooks**: You cannot commit badly formatted code. `black`, `ruff`, and `mypy` will block you automatically (configured via `make setup`).
2. **Pytest**: Run `make test` to execute the mock-heavy `pytest` test suite.
3. **E2E Validation**: Start the entire stack (`make local-run`) and execute our automated curl-based sanity script to verify the end-to-end integration works across the API boundaries:
   ```bash
   make e2e-curl
   ```

### Continuous Integration (GitHub Actions)
Our current `.github/workflows/ci.yml` strictly guards code quality in two distinct phases:
1. **Fast Checks (Lint & Typecheck)**: Triggers on *every* code push to a PR. It runs `pre-commit` to guarantee syntax formatting and typing logic (`black`, `ruff`, `mypy`).
2. **Heavy Checks (Security & Unit Tests)**: Runs on direct pushes and PRs. It executes the heavy `pytest` suite and additionally runs `bandit` security scans over the entire codebase to detect common security flaws before code is merged.
