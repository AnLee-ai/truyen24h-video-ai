-- Enable vector extension for semantic search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Table: novels
CREATE TABLE IF NOT EXISTS novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'writing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: chapters
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE NOT NULL,
    chapter_number INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    audio_url TEXT,
    video_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    video_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE (novel_id, chapter_number)
);

-- Migration SQL for existing databases:
-- ALTER TABLE chapters ADD COLUMN IF NOT EXISTS video_status VARCHAR(50) DEFAULT 'pending';
-- ALTER TABLE chapters ADD COLUMN IF NOT EXISTS video_url TEXT;

-- Table: episodes_summary
CREATE TABLE IF NOT EXISTS episodes_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE NOT NULL,
    event_summary TEXT NOT NULL,
    embedding VECTOR(1536), -- Vector representation for semantic search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: characters
CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    power_tier VARCHAR(100) NOT NULL DEFAULT 'Ordinary',
    combat_stats JSONB DEFAULT '{}'::jsonb,
    relationships JSONB DEFAULT '{}'::jsonb,
    failure_flag BOOLEAN DEFAULT false NOT NULL,
    last_breakthrough_chapter INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE (novel_id, name)
);

-- Table: world_lore
CREATE TABLE IF NOT EXISTS world_lore (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE (novel_id, keyword)
);

-- Table: narrative_threads
CREATE TABLE IF NOT EXISTS narrative_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE NOT NULL,
    thread_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open', -- 'open' or 'resolved'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Function: match_episodes for pgvector similarity search
CREATE OR REPLACE FUNCTION match_episodes(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  novel_id_filter uuid
)
RETURNS TABLE (
  id uuid,
  chapter_id uuid,
  event_summary text,
  similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    es.id,
    es.chapter_id,
    es.event_summary,
    1 - (es.embedding <=> query_embedding) AS similarity
  FROM episodes_summary es
  JOIN chapters c ON es.chapter_id = c.id
  WHERE c.novel_id = novel_id_filter
    AND 1 - (es.embedding <=> query_embedding) > match_threshold
  ORDER BY es.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Disable Row Level Security (RLS) for all tables to allow direct client access
ALTER TABLE novels DISABLE ROW LEVEL SECURITY;
ALTER TABLE chapters DISABLE ROW LEVEL SECURITY;
ALTER TABLE episodes_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE characters DISABLE ROW LEVEL SECURITY;
ALTER TABLE world_lore DISABLE ROW LEVEL SECURITY;
ALTER TABLE narrative_threads DISABLE ROW LEVEL SECURITY;

