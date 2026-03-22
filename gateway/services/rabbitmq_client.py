import aio_pika
import json
from gateway.core.config import settings


async def publish_document_event(document_id: str, file_path: str, tenant_id: str):
    """
    Publishes an event to RabbitMQ whenever a new document is successfully saved to MinIO.
    This tells the Processing Worker to start extracting data.
    """
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()

        # Declare queue (ensures it exists before publishing)
        await channel.declare_queue(settings.RABBITMQ_QUEUE_NAME, durable=True)

        message_body = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "file_path": file_path,
            "action": "process_document",
        }

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.RABBITMQ_QUEUE_NAME,
        )
