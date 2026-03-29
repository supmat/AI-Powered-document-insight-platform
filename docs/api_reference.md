# AI-Powered Document Insight Platform API Reference

This document outlines the core REST API endpoints available for frontend integration. The API is built with FastAPI and runs on `http://localhost:8001/api/v1` locally.

All protected routes require an `Authorization` header containing a valid Bearer Token.

---

## Authentication API

### 1. Register User
Creates a new user account.

- **URL**: `/api/v1/auth/register`
- **Method**: `POST`
- **Auth Required**: No
- **Headers**: `Content-Type: application/json`

**Request Body (`application/json`)**
```json
{
  "email": "user@example.com",
  "password": "your_secure_password",
  "full_name": "Alice Developer"
}
```

**Response (200 OK)**
```json
{
  "msg": "User created successfully. You can now login!"
}
```

### 2. Login (Get Token)
Authenticates a user and returns a JWT access token. Note that this uses FastAPI's `OAuth2PasswordRequestForm` under the hood, so it expects `application/x-www-form-urlencoded`.

- **URL**: `/api/v1/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Headers**: `Content-Type: application/x-www-form-urlencoded`

**Request Body (`application/x-www-form-urlencoded`)**
```
username=user@example.com
password=your_secure_password
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## Document Management API

### 3. Upload Documents
Uploads one or many documents (PDF, JPG, PNG) for background vectorization processing.

- **URL**: `/api/v1/upload_documents/`
- **Method**: `POST`
- **Auth Required**: Yes (`Bearer Token`)
- **Headers**: `Content-Type: multipart/form-data`

**Request Form Data**
- `files`: File objects. Can be passed multiple times to upload in batch. Max 50MB per file.

**Response (202 Accepted)**
The request returns immediately while processing begins in the background.
```json
{
  "message": "1 documents received and scheduled.",
  "tasks": [
    {
      "task_id": "8d1032bf-74d5-41bc-8ae7-aed87ca20710",
      "filename": "test_document.pdf",
      "status": "PENDING"
    }
  ]
}
```

### 4. List User Documents
Returns a deduplicated list of all documents successfully ingested for the current authenticated user, including the total number vectors (chunks) stored per document.

- **URL**: `/api/v1/documents/`
- **Method**: `GET`
- **Auth Required**: Yes (`Bearer Token`)

**Response (200 OK)**
```json
{
  "total": 1,
  "documents": [
    {
      "document_id": "8d1032bf-74d5-41bc-8ae7-aed87ca20710",
      "filename": "test_document.pdf",
      "chunk_count": 5,
      "tenant_id": "user@example.com"
    }
  ]
}
```

### 5. Delete Document
Permanently deletes all vectors/chunks associated with a specific document. Users can only delete their own data.

- **URL**: `/api/v1/documents/{document_id}`
- **Method**: `DELETE`
- **Auth Required**: Yes (`Bearer Token`)

**Path Parameters**
- `document_id`: The ID returned during upload.

**Response (200 OK)**
```json
{
  "message": "Document '8d1032bf-...' deleted successfully.",
  "document_id": "8d1032bf-74d5-41bc-8ae7-aed87ca20710",
  "chunks_deleted": 5
}
```

---

## Retrieval-Augmented Generation (RAG) API

### 6. Ask Question (Query)
Takes a natural language question, searches the vector database for relevant text chunks, and uses Gemini 2.0 to generate an answer backed by the provided semantic context.

- **URL**: `/api/v1/query/`
- **Method**: `POST`
- **Auth Required**: Yes (`Bearer Token`)
- **Headers**: `Content-Type: application/json`

**Request Body (`application/json`)**
```json
{
  "question": "What is the secret code for the platform?",
  "top_k": 5,
  "filter": {}
}
```
*Note: `top_k` (default: 5) and `filter` are optional parameters. The backend securely forces a tenant-level filter automatically based on your token.*

**Response (200 OK)**
```json
{
  "answer": "The secret code for the document insight platform is 42-ALPHA-ZULU.",
  "confidence_score": 0.85,
  "quoted_sources": [
    {
      "document_id": "8d1032bf-74d5-41bc-8ae7-aed87ca20710",
      "filename": "test_document.pdf",
      "text_snippet": "The secret code for the document insight platform is 42-ALPHA-ZULU..."
    }
  ],
  "detected_entities": [
    "42-ALPHA-ZULU"
  ]
}
```
