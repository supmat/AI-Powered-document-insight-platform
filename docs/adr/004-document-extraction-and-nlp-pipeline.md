# ADR 004: Document Extraction and NLP Pipeline Architecture

## Status
Accepted

## Context
The AI-Powered Document Insight Platform needs a robust and scalable pipeline to reliably extract raw text from uploaded files (PDFs, Images), dynamically process the text in multiple languages, and enrich the corpus with Named Entity Recognition (NER) context before generating AI embeddings. The system must account for missing AI API keys, multi-lingual documents, and memory-safe processing limits.

## Decisions

### 1. Document Reading & Optical Character Recognition (OCR)
- **PDF Extraction**: **PyMuPDF (`fitz`)** for strict PDF extraction. It is widely considered the fastest Python PDF parser with low memory overhead, enabling near-instantaneous text ripping from structured PDFs.
- **Image OCR**: For image files (`.png`, `.jpg`), plan is to implement a **Hybrid Extraction Strategy**.
  - *Primary Route*: Stream the image bytes directly to the **Google Gemini 1.5 Vision API**. This offloads all complex OCR compute to external cloud GPUs and provides phenomenally accurate semantic understanding of complex layouts (tables, forms).
  - *Fallback Route*: In the event the `GEMINI_API_KEY` is missing or the network drops cleanly, the pipeline will fall back to **EasyOCR** loaded into local memory.
    - **OpenCV Image Polishing**: Before feeding the raw pixel array into the EasyOCR neural network, the pipeline will utilize OpenCV (`cv2`) to mathematically polish the image. It converts the frame to grayscale, applies a Gaussian blur to aggressively remove scan artifact noise, and runs Otsu's algorithmic thresholding to strictly binarize the image (black/white). This guarantees text contrast is mathematically maximized, radically boosting EasyOCR's extraction precision across low-quality desktop scans.

### 2. Polyglot Language Detection
- **Dynamic NLP Routing**: Not all documents are in English. Instead of failing blindly, plan is to integrate the **`langdetect`** library. By evaluating the text chunks statistically, the pipeline will accurately infer the underlying ISO language code (e.g., `es`, `fr`, `de`).

### 3. Named Entity Recognition (NER)
- **Local spaCy Engine**: Plan is to use **`spaCy`** to perform localized, free Named Entity Recognition instead of relying exclusively on cloud AI to identify people, organizations, and geographical locations. By caching this work locally, dramatically reduces LLM token costs.
- **Auto-Downloading Localized Models**: Based on the ISO language code resolved by `langdetect`, the pipeline actively maps and routes the text to the correct, localized spaCy Neural Network model (e.g. `fr_core_news_sm`). If the multi-lingual model doesn't exist on the Docker host machine, the pipeline programmatically downloads it (`spacy.cli.download`) at runtime, caching it safely into memory for all future queries.

### 4. Vector Embeddings
- **AI Embedding Generation**: For semantic vector search, it's required high-dimensional mappings of the extracted text.
  - *Primary Route*: Hit the **Google Gemini API (`text-embedding-004`)** to generate 768-dimensional float vectors. This is blazingly fast and offloads all heavy computation to the cloud.
  - *Fallback Route*: If the `GEMINI_API_KEY` is missing or the network drops cleanly, the pipeline automatically falls back to a locally hosted **Sentence Transformers** model (`all-mpnet-base-v2`). Crucially, this specific open-source HuggingFace model also natively produces exactly **768 dimensions**. This guarantees perfect structural compatibility with our strict Postgres `pgvector` database schema, preventing catastrophic geometry dimension mismatches in SQL during seamless fallbacks.

## Consequences
- **Positive**:
  - Massive infrastructure resilience via graceful fallbacks (Gemini -> EasyOCR).
  - Out-of-the-box support for dozens of localized languages without manual pipeline manual tagging.
  - Zero external API cost strictly for identifying basic organizational entities.
- **Negative**:
  - The Worker Docker image size naturally increases because `spaCy` multi-language models and `EasyOCR` PyTorch weights must be cached locally.
  - The first time a completely new language is detected by `langdetect`, processing will be paused for approximately ~15 seconds while the specific `spaCy` language model downloads synchronously over the network.
