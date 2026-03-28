import asyncio
import aio_pika
import json
from processing.core.config import settings
from processing.services.minio_client import download_file_from_minio
from processing.services.pdf_extractor import extract_text_from_pdf
from query.services.gemini_client import get_embeddings
from processing.services.image_extractor import extract_text_from_image
from processing.services.chunker import chunk_text
from processing.services.ner_client import extract_entities
from processing.services.db_client import init_db, store_document_chunks


async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            doc_id = payload.get("document_id")
            tenant_id = payload.get("tenant_id")
            file_path = payload.get("file_path")

            print(
                f"[*] Starting processing for document {doc_id} by tenant {tenant_id}"
            )

            # Step 1. Download file
            file_bytes = download_file_from_minio(file_path)

            # Step 2. Extract Text
            filename = file_path.split("/")[-1]
            if filename.lower().endswith(".pdf"):
                text_corpus = extract_text_from_pdf(file_bytes)
            elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
                text_corpus = await extract_text_from_image(file_bytes)
            else:
                raise ValueError(f"Unknown file extension for {filename}")

            if not text_corpus:
                print(f"[!] No text found in {filename}. Skipping chunking.")
                return

            # Step 3. Chunk text & NER
            chunks = chunk_text(text_corpus)
            entities_list = [extract_entities(chunk) for chunk in chunks]

            # Step 4. Gemini Embeddings / local embeddings
            embeddings = await get_embeddings(chunks)

            # Step 5. Save to pgvector
            await store_document_chunks(
                document_id=doc_id,
                tenant_id=tenant_id,
                filename=filename,
                chunks=chunks,
                embeddings=embeddings,
                entities_list=entities_list,
            )

            print(
                f"[*] Successfully processed and vectorized document {doc_id} ({len(chunks)} chunks)"
            )
        except Exception as e:
            print(f"[!] Error processing message: {e}")


async def main():
    print("[*] Initializing Database Subsystem...")
    await init_db()

    print("[*] Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()

        # Ensuring queue is resilient and matches Gateway configuration
        queue = await channel.declare_queue(settings.RABBITMQ_QUEUE_NAME, durable=True)

        print(
            f"[*] Processing Worker actively polling on queue: {settings.RABBITMQ_QUEUE_NAME}..."
        )

        # Start consuming messages
        await queue.consume(process_message)

        # Block the event loop forever
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
