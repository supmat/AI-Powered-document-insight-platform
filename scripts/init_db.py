import asyncio
from shared.database import init_db as shared_init
from processing.services.db_client import init_db as processing_init


async def main():
    print("[*] Waiting for PostgreSQL to be ready...")
    # Simple retry loop to wait for the database container to boot
    for i in range(10):
        try:
            print(
                f"[*] Bootstrapping Database Schema and Extensions (Attempt {i+1}/10)..."
            )
            # 1. Initialize processing specific needs (pgvector extension)
            await processing_init()
            # 2. Initialize shared models (Tables)
            await shared_init()
            print("[*] Database Bootstrap Complete.")
            return
        except Exception as e:
            print(f"[*] Postgres not ready yet... ({e})")
            await asyncio.sleep(2)

    print("[ERROR!] PostgreSQL failed to become ready in time.")
    exit(1)


if __name__ == "__main__":
    asyncio.run(main())
