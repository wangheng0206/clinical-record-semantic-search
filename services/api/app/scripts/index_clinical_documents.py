import asyncio
import logging
import sys

from app.clients.embedding import EmbeddingClient
from app.config import get_settings
from app.db.pool import open_pool
from app.errors import EmbeddingServiceError
from app.features.indexing.runner import index_documents
from app.observability import configure_logging

logger = logging.getLogger("api.scripts.index")


async def run() -> int:
    settings = get_settings()
    embedding = EmbeddingClient(
        base_url=settings.embedding_service_url,
        timeout_seconds=settings.embedding_request_timeout_seconds,
        max_batch_size=settings.embedding_max_batch_size,
    )
    try:
        if not await embedding.is_healthy():
            print("embedding service is not healthy; start it and retry", file=sys.stderr)
            return 1
        async with open_pool(settings.database_url, min_size=1, max_size=2) as pool:
            summary = await index_documents(pool, embedding)
    except EmbeddingServiceError:
        print("embedding service failed during indexing; rerun to resume", file=sys.stderr)
        return 1
    finally:
        await embedding.aclose()

    print(
        f"scanned={summary.scanned} skipped_unchanged={summary.skipped_unchanged} "
        f"indexed={summary.indexed} failed={summary.failed} "
        f"chunks_written={summary.chunks_written} duration_s={summary.duration_seconds}"
    )
    for failure in summary.failures:
        print(f"failed document_id={failure.document_id} reason={failure.reason}")
    return 0


def main() -> int:
    configure_logging(get_settings().api_log_level)
    try:
        return asyncio.run(run())
    except Exception as exc:
        logger.error("indexing failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
