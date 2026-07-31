CREATE TABLE document_index_state (
    document_id      text PRIMARY KEY REFERENCES clinical_documents (id) ON DELETE CASCADE,
    content_hash     text NOT NULL,
    chunk_count      integer NOT NULL,
    status           text NOT NULL,
    failure_reason   text,
    indexed_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_index_state_status_allowed CHECK (status IN ('indexed', 'failed'))
);

CREATE TABLE document_chunks (
    id              text PRIMARY KEY,
    document_id     text NOT NULL REFERENCES clinical_documents (id) ON DELETE CASCADE,
    practice_id     text NOT NULL REFERENCES practices (id) ON DELETE CASCADE,
    patient_id      text NOT NULL REFERENCES patients (id) ON DELETE CASCADE,
    document_type   document_type NOT NULL,
    chunk_index     integer NOT NULL,
    content         text NOT NULL,
    embedding       vector(384) NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_chunks_document_chunk_key UNIQUE (document_id, chunk_index),
    CONSTRAINT document_chunks_content_not_blank CHECK (btrim(content) <> '')
);

CREATE INDEX document_chunks_practice_type_idx
    ON document_chunks (practice_id, document_type);
CREATE INDEX document_chunks_patient_idx ON document_chunks (patient_id);
CREATE INDEX document_chunks_embedding_hnsw_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
