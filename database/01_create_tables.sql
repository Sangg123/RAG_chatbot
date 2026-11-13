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
-- 8. orders
--    Du lieu don hang co cau truc de AI tra cuu qua function calling.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id                 UUID          PRIMARY KEY,
    user_id            UUID          NOT NULL,
    order_code         VARCHAR(32)   NOT NULL,
    customer_name      VARCHAR(255)  NOT NULL,
    customer_phone     VARCHAR(32)   NOT NULL,
    shipping_address   TEXT          NOT NULL,
    status             VARCHAR(32)   NOT NULL,
    payment_method     VARCHAR(32),
    payment_status     VARCHAR(32),
    subtotal           NUMERIC(12,2) NOT NULL DEFAULT 0,
    shipping_fee       NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount       NUMERIC(12,2) NOT NULL DEFAULT 0,
    carrier            VARCHAR(100),
    tracking_code      VARCHAR(100),
    ordered_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    estimated_delivery TIMESTAMPTZ,
    delivered_at       TIMESTAMPTZ,
    note               TEXT,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ,
    CONSTRAINT fk_orders_user_id_users
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_code
    ON orders (order_code);
CREATE INDEX IF NOT EXISTS ix_orders_customer_phone
    ON orders (customer_phone);
CREATE INDEX IF NOT EXISTS ix_orders_status
    ON orders (status);
CREATE INDEX IF NOT EXISTS ix_orders_user_id
    ON orders (user_id);

-- ---------------------------------------------------------------------------
-- 9. order_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id           UUID          PRIMARY KEY,
    order_id     UUID          NOT NULL,
    product_name VARCHAR(255)  NOT NULL,
    quantity     INTEGER       NOT NULL DEFAULT 1,
    unit_price   NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id
    ON order_items (order_id);

-- ---------------------------------------------------------------------------
-- 10. message_tool_calls
--     Audit log moi lan AI goi tool (arguments/result JSONB).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS message_tool_calls (
    id            UUID         PRIMARY KEY,
    message_id    UUID         NOT NULL,
    tool_name     VARCHAR(64)  NOT NULL,
    arguments     JSONB,
    result        JSONB,
    status        VARCHAR(20)  NOT NULL DEFAULT 'success',
    error_message TEXT,
    duration_ms   INTEGER,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_message_tool_calls_message
        FOREIGN KEY (message_id)
        REFERENCES messages (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_message_tool_calls_message_id
    ON message_tool_calls (message_id);
CREATE INDEX IF NOT EXISTS ix_message_tool_calls_tool_name
    ON message_tool_calls (tool_name);

-- ---------------------------------------------------------------------------
-- 11. alembic_version
--    Danh dau migration moi nhat de backend co the chay
--    "alembic upgrade head" ma khong bi loi "table already exists".
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num)
VALUES ('20261117_000006')
ON CONFLICT (version_num) DO NOTHING;

COMMIT;
