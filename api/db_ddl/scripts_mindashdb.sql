select * from documents_rag


-- 1. Habilitar la extensión 'vector' (solo se hace una vez por base de datos)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Crear la tabla para los documentos RAG
CREATE TABLE IF NOT EXISTS documents_rag (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    chunk_id INTEGER NOT NULL,
    -- Aquí ya NO usamos {DIMENSION}, sino el número real.
    embedding vector(768) 
);

-- 3. (Opcional pero recomendado): Crear un índice eficiente sobre la columna 'embedding'
-- Esto es CRÍTICO para búsquedas rápidas con pgvector.
-- Usa HNSW para grandes volúmenes de datos o IVFFlat si tienes menos de 1 millón de vectores.
CREATE INDEX ON documents_rag USING HNSW (embedding vector_l2_ops);



select * from documents_rag;