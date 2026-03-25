from google import genai
from google.genai import types
from processing.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential
from sentence_transformers import SentenceTransformer

_client = (
    genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
)

# Cache the local embedding model globally
local_embedder = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates high-quality vector embeddings for an array of text chunks.
    Attempts to use Gemini text-embedding-004.
    Falls back to local all-mpnet-base-v2 (768 dimensions) if Gemini fails.
    """
    if _client:
        try:
            result = _client.models.embed_content(
                model="models/text-embedding-004",
                contents=texts,
                config=types.EmbedContentConfig(task_type="retrieval_document"),
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            print(f"[!] Gemini Embeddings failed, falling back to local ML model: {e}")

    # Fallback to local SentenceTransformer (MUST be 768-D to match pgvector schema)
    global local_embedder
    if local_embedder is None:
        print(
            "[*] Initializing local 'all-mpnet-base-v2' (768-D) Embedding model into memory..."
        )
        local_embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

    embeddings = local_embedder.encode(texts)
    return embeddings.tolist()
