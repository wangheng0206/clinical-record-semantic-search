# Indexing workflow

The entry point `app/scripts/index_clinical_documents.py` is implemented.

```bash
make index
```

The workflow chunks clinical documents (paragraph packing with overlap), embeds them
through the provided embedding service, and stores them in `document_chunks`. A
per-document content hash in `document_index_state` drives change detection: re-runs
skip unchanged documents, re-index changed ones inside one transaction per document,
and record an individual unindexable document as `failed` with a reason instead of
aborting the run. A completion summary reports scanned/indexed/skipped/failed counts
plus failed document ids.
