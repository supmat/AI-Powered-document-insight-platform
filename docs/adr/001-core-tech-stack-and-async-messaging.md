# Title: 001. Selection of Core Framework and Asynchronous Messaging
Status: Accepted
Date: 2026-03-21

## Context
Production-ready Document Insight Platform that needs to ingest large files (≥ 10 MiB) and perform heavy machine learning operations like OCR, NER, and embedding generation. Processing these synchronously would lead to HTTP timeouts and a poor user experience. Furthermore, core services must be written in Python. Decision is needed for a web framework and a mechanism for background processing.

## Decision
Use FastAPI as our core web framework for all API services (Gateway, Ingestion, Query) and RabbitMQ combined with a standalone Python worker for asynchronous processing.

## Rationale

- FastAPI: It is highly performant, natively supports asynchronous I/O, and automatically generates OpenAPI documentation. Its reliance on Pydantic enforces strict type hinting, aligning perfectly with our requirement for idiomatic Python and high code quality.

- RabbitMQ: RabbitMQ is a robust, cloud-native message broker. By emitting events from the Ingestion Service to RabbitMQ, we decouple the API from the heavy ML processing. This prevents the web server from blocking and allows us to easily scale the Processing Worker horizontally if the ingestion queue backs up.

## Consequences

- Positive: Clean decoupling of services, excellent performance, and built-in type safety.

- Negative/Risk: Introducing RabbitMQ adds infrastructure complexity compared to a simpler solution like an in-memory queue. However, it realistically simulates a cloud-native production environment and meets the requirement to emit an event for downstream processing.
