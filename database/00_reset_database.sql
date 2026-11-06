-- ============================================================================
-- RAG Chatbot - XOA toan bo bang (chi dung khi muon lam lai tu dau)
-- CANH BAO: xoa sach du lieu trong database rag_chatbot
-- Chay file nay, sau do chay lai 01_create_tables.sql va 02_seed_data.sql
-- ============================================================================

BEGIN;

DROP TABLE IF EXISTS message_citations CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS knowledge_bases CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

COMMIT;
