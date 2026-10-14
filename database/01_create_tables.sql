-- ============================================================================
-- RAG Chatbot - Tao cau truc database (PostgreSQL + pgvector)
-- Database dich: rag_chatbot
-- Cach chay tren pgAdmin: chuot phai database rag_chatbot > Query Tool
--                        > mo file nay > Execute (F5)
-- ============================================================================

-- Bat buoc phai co extension pgvector (can quyen superuser, thuong la postgres)
CREATE EXTENSION IF NOT EXISTS vector;

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID         PRIMARY KEY,
    username        VARCHAR(100) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'user',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    token_version   INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email    ON users (email);

-- ---------------------------------------------------------------------------
-- 2. knowledge_bases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id          UUID         PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 3. documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id                UUID         PRIMARY KEY,
    knowledge_base_id UUID         NOT NULL,
    filename          VARCHAR(255) NOT NULL,
    file_type         VARCHAR(50),
    file_url          TEXT,
    upload_status     VARCHAR(50),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_documents_knowledge_base
        FOREIGN KEY (knowledge_base_id)
        REFERENCES knowledge_bases (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_documents_knowledge_base_id
    ON documents (knowledge_base_id);

-- ---------------------------------------------------------------------------
-- 4. document_chunks
--    embedding: vector khong gioi han so chieu (du lieu that dung 768 chieu
--    voi model embeddinggemma cua Ollama)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id          UUID        PRIMARY KEY,
    document_id UUID        NOT NULL,
    content     TEXT        NOT NULL,
    embedding   VECTOR,
    chunk_index INTEGER,
    CONSTRAINT fk_document_chunks_document
        FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id
    ON document_chunks (document_id);

-- ---------------------------------------------------------------------------
-- 5. conversations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id         UUID         PRIMARY KEY,
    user_id    UUID         NOT NULL,
    title      VARCHAR(255),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT fk_conversations_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_conversations_user_id
    ON conversations (user_id);

-- ---------------------------------------------------------------------------
-- 6. messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id              UUID        PRIMARY KEY,
    conversation_id UUID        NOT NULL,
    sender_type     VARCHAR(50) NOT NULL,
    content         TEXT        NOT NULL,
    rating          INTEGER,
    feedback_text   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id
    ON messages (conversation_id);

-- ---------------------------------------------------------------------------
-- 7. message_citations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS message_citations (
    id              UUID    PRIMARY KEY,
    message_id      UUID    NOT NULL,
    chunk_id        UUID    NOT NULL,
    relevance_score DOUBLE PRECISION,
    CONSTRAINT fk_message_citations_message
        FOREIGN KEY (message_id)
        REFERENCES messages (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_message_citations_chunk
        FOREIGN KEY (chunk_id)
        REFERENCES document_chunks (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_message_citations_message_id
    ON message_citations (message_id);
CREATE INDEX IF NOT EXISTS ix_message_citations_chunk_id
    ON message_citations (chunk_id);

-- ---------------------------------------------------------------------------
-- 8. alembic_version
--    Danh dau migration moi nhat de backend co the chay
--    "alembic upgrade head" ma khong bi loi "table already exists".
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num)
VALUES ('20260411_000004')
ON CONFLICT (version_num) DO NOTHING;

COMMIT;
