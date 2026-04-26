import asyncio
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Tuple, Any
from shared.models import DocumentChunk
from processing.core.config import settings
from shared.security import SecretService
from tenacity import retry, stop_after_attempt, wait_exponential

_client = (
    genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
)

# Initialize secure service for Task 7.4
secrets = SecretService(settings.DATA_ENCRYPTION_KEY)

# Cache the local embedding model globally
local_embedder = None

# Global variable to hold our local model in memory only if needed
_local_llm_pipeline = None


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=20),
    reraise=True,
)
async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates high-quality vector embeddings for an array of text chunks.
    Attempts to use Gemini embedding 001 forcing 768 dimensions.
    Will retry up to 5 times.
    """
    if not _client:
        raise RuntimeError("Gemini client is not initialized")

    try:
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768
        )

        result = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
            config=config,
        )
        return [e.values[:768] for e in result.embeddings]

    except Exception as e:
        print(f"[ERROR!] Gemini model failed: {e}")
        # Re-raise to trigger Tenacity retry
        raise TimeoutError("Embedding system failed with timeout") from e


def _get_local_llm():
    """Lazily loads a lightweight local LLM if Gemini is unavailable."""
    global _local_llm_pipeline
    if _local_llm_pipeline is None:
        print(
            "[*] GEMINI_API_KEY not found. Loading local TinyLlama fallback model... (This may take a minute on first run)"
        )
        # We import here so the app doesn't require these packages if using Gemini
        from transformers import pipeline

        # TinyLlama is small enough (~1.1B params) to run reasonably well on a standard CPU
        _local_llm_pipeline = pipeline(
            "text-generation",
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            device="cpu",  # Explicitly use CPU as per your laptop setup
            max_new_tokens=200,
        )
        print("[*] Local fallback LLM loaded successfully.")
    return _local_llm_pipeline


def _generate_local_answer(prompt: str) -> str:
    """Synchronous function to run the local Hugging Face pipeline."""
    llm = _get_local_llm()
    # Format the prompt specifically for TinyLlama's chat template
    formatted_prompt = (
        f"<|system|>\nYou are a helpful AI assistant.<|user|>\n{prompt}<|assistant|>\n"
    )

    result = llm(formatted_prompt, return_full_text=False)
    return result[0]["generated_text"].strip()


async def retrieve_relevant_chunks(
    db: AsyncSession, question_embedding: list[float], filters: Dict, top_k: int
) -> List[Tuple[Any, Any]]:
    # Calculate the distance and label it
    distance_col = DocumentChunk.embedding.cosine_distance(question_embedding).label(
        "distance"
    )

    """Retrieves passages matching the vector and the applied filter."""
    stmt = select(DocumentChunk, distance_col)

    if filters and "tenant_id" in filters:
        stmt = stmt.where(DocumentChunk.tenant_id == filters["tenant_id"])

    stmt = stmt.order_by(distance_col).limit(top_k)
    result = await db.execute(stmt)
    rows = result.all()

    # Task 7.4: Decrypt each chunk's text content after retrieval from the DB
    decrypted_chunks = []
    for row in rows:
        chunk = row[0]
        chunk.text_content = secrets.decrypt_text(chunk.text_content)
        decrypted_chunks.append((chunk, row[1]))

    return decrypted_chunks


async def generate_rag_answer(question: str, chunks: List[DocumentChunk]) -> str:
    """Calls Gemini API via SDK, or falls back to a local CPU-based LLM."""
    if not chunks:
        return "I could not find any relevant documents to answer your question."

    # Task 7.4: Decrypt each chunk's text content before passing to the LLM
    context_text = "\n\n---\n\n".join([chunk.text_content for chunk in chunks])
    prompt = f"""
    Answer the question based ONLY on the provided context below.
    If the answer is not in the context, truthfully say "I cannot answer this based on the provided documents."

    Context:
    {context_text}

    Question: {question}
    Answer:
    """

    # We can ask LLM to calculate confidence score, but we can't be sure that LLM is not halucinating the score
    # So we will use confidence score based on vector retrieval from DB
    # confidence_score = 0.85

    # --- PRIMARY ROUTE: GEMINI SDK ---
    if _client:
        try:
            # This allows FastAPI to handle thousands of other requests
            # while r Google's servers to reply.
            response = await _client.aio.models.generate_content(
                model="gemini-2.5-flash",  # Matching common Gemini 2.0 usage
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            if response and response.text:
                return response.text

        except Exception as e:
            print(f"[ERROR!] Gemini SDK Error: {e}. Falling back to local model...")
            # Fall through to local model
            pass

    # --- BACKUP ROUTE: LOCAL CPU LLM ---
    try:
        # We must run the local model in a separate thread so it doesn't block FastAPI's async event loop
        answer = await asyncio.to_thread(_generate_local_answer, prompt)
        return answer
    except Exception as e:
        print(f"[ERROR!] Local LLM Error: {e}")
        return (
            "Sorry, both the primary LLM and the local fallback encountered an error."
        )
