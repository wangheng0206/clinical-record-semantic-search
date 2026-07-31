import asyncpg

from app.config import Settings
from app.db.migrations import apply_migrations


async def test_migrations_rerun_is_a_noop(prepared_database: str, settings: Settings) -> None:
    pool = await asyncpg.create_pool(dsn=prepared_database, min_size=1, max_size=1)
    try:
        result = await apply_migrations(pool, settings.migrations_dir)
    finally:
        await pool.close()

    assert result.applied == []
    assert set(result.skipped) == {"0001_base_schema.sql", "0002_document_chunks.sql"}
