# Title: 003. AI Services and Data Storage
Status: Accepted
Date: 2026-03-21

## Context
The platform needs robust external dependencies for two major machine learning workloads:
1. Generating embeddings and answering queries iteratively using a Large Language Model (LLM).
2. Storing unstructured vector data representing indexed documents, and retrieving them efficiently while guaranteeing tenant-level data isolation.

## Decision
1. **LLM Integration:** Integrate the **Google Gemini API** for natural language understanding and text generation (e.g., summarization and reasoning over extracted snippets).
2. **Vector Store & Relational DB:** Choose **PostgreSQL with the `pgvector` extension** as the primary datastore for both vector embeddings and system metadata.

## Rationale
- **Google Gemini API:** Using an established proprietary model like Gemini allows the team to fast-track development without managing enormous GPUs or paying for expensive infrastructure upfront. Gemini models have powerful long-context capabilities window making them an excellent choice for analyzing and reasoning over extracted document chunks. It perfectly aligns with the required capability of generating answers based on retrieved context (Retrieval-Augmented Generation).
- **PostgreSQL (pgvector):** By leveraging PostgreSQL with the `pgvector` extension, we significantly simplify the infrastructure stack. Instead of running a separate dedicated vector database (like Qdrant) alongside a relational database for user/tenant data, PostgreSQL handles both seamlessly. This reduces operational complexity, leverages familiar SQL tooling, and handles multi-tenancy flawlessly through standard `WHERE tenant_id = <ID>` clauses (or Row-Level Security).

## Consequences
- **Positive:** Massive reduction in initial deployment complexity. The platform relies on a highly scalable cloud LLM to perform heavy lifting and a single, battle-tested PostgreSQL database handling both our relational needs and vector search, drastically lowering operational overhead and leveraging team familiarity with SQL.
- **Negative/Risk:** Dependence on a third-party paid API for the core reasoning component incurs future variable costs and relies on external uptime SLA. Data compliance should be ensured if processing highly sensitive non-public documents, requiring adherence to the enterprise data processing terms of Google Cloud.
