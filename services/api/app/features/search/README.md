# Semantic search API

`router.py` is implemented.

The endpoint returns a ranked, practice-isolated list of unique patients with supporting
evidence from the indexed source documents. Requests are validated, semantic retrieval runs
through the embedding service, and dependency failures use the shared client-safe error path
without leaking internals.

The query shape, ranking strategy, patient aggregation, evidence selection, and database
access design are yours to implement and justify. Follow the contracts and observable
requirements in `docs/TAKE_HOME_DESIGN.md`.
