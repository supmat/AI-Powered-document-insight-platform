# Title: 002. Infrastructure, Worker Management, and Authentication
Status: Accepted
Date: 2026-03-21

## Context
Deploying the AI-powered Document Insight Platform requires defining how the system runs across environments (local vs. cloud), how asynchronous processing workers are managed, and how system access is secured in a stateless manner suitable for API/Gateway communication.

## Decision
1. **Deployment Architecture:** Use **Docker Compose** for local development and **Kubernetes (K8s)** for cloud-native deployment.
2. **Worker Management:** Package the Python processing worker (consuming from RabbitMQ) into a separate Docker container managed via K8s Deployments (cloud) and a dedicated compose service (local).
3. **Authentication:** Implement **JWT (JSON Web Tokens)** for stateless authentication.

## Rationale
- **Docker Compose & Kubernetes:** Docker Compose provides a frictionless local development experience, enabling developers to spin up the gateway, workers, RabbitMQ, and databases with a single `make local-run` command. Kubernetes is the industry standard for cloud-native container orchestration, providing built-in features for secrets management, self-healing, rolling updates, and horizontal auto-scaling based on CPU/Memory or custom metrics (e.g., RabbitMQ queue length).
- **Worker Management:** Using standalone Python workers in containers decoupled from the web servers means we can scale the web API and background ML processing independently. Kubernetes deployments make it trivial to increase replica counts for the worker independently of the ingestion API.
- **JWT (JSON Web Tokens):** For the Gateway / BFF, JWT provides a stateless mechanism to verify user identity without querying a centralized session database on every request.
  - **Usage:** Clients obtain a JWT upon login and pass it in the `Authorization: Bearer <token>` header for subsequent requests.
  - **Storage:** For API clients, the token should be kept securely in memory. If a frontend UI is developed later, the JWT should be stored in an `HttpOnly`, `Secure` cookie to mitigate XSS attacks while the BFF handles token extraction.

## Consequences
- **Positive:** Clear separation of concerns, excellent scalability across environments, and a stateless integration model that simplifies Gateway logic.
- **Negative/Risk:** Managing Kubernetes adds operational overhead and requires infrastructure-as-code (e.g., Helm charts or Kustomize). Implementing proper JWT revocation (e.g., on logout) forces either short expirations (preferred) or maintaining a token blocklist.
