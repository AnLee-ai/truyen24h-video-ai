-- ============================================================================
-- SUPABASE MASTER DATABASE SCHEMA: 12 BẢNG CSDL DOANH NGHIỆP TRUYỆN 24H AI
-- ============================================================================

-- 1. BANG NOVELS (Tiểu thuyết)
CREATE TABLE IF NOT EXISTS public.novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT UNIQUE NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'writing',
    cover_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. BANG CHARACTERS (Nhân vật)
CREATE TABLE IF NOT EXISTS public.characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    power_tier TEXT,
    combat_stats JSONB DEFAULT '{}'::jsonb,
    relationships JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_novel_character UNIQUE (novel_id, name)
);

-- 3. BANG WORLD_LORE (Bối cảnh thế giới)
CREATE TABLE IF NOT EXISTS public.world_lore (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_novel_keyword UNIQUE (novel_id, keyword)
);

-- 4. BANG NARRATIVE_THREADS (Tuyến cốt truyện & Arc)
CREATE TABLE IF NOT EXISTS public.narrative_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    novel_title TEXT,
    thread_name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. BANG CHAPTERS (Tập truyện & Media status)
CREATE TABLE IF NOT EXISTS public.chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    chapter_number INT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    audio_url TEXT,
    video_url TEXT,
    video_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_novel_chapter_number UNIQUE (novel_id, chapter_number)
);

-- 6. BANG EPISODES_SUMMARY (Tóm tắt chương)
CREATE TABLE IF NOT EXISTS public.episodes_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES public.chapters(id) ON DELETE CASCADE,
    event_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 6 BẢNG MỚI NÂNG CẤP DOANH NGHIỆP (ENTERPRISE EXTENSIONS)
-- ----------------------------------------------------------------------------

-- 7. BANG PUBLISHING_ANALYTICS (Thống kê tương tác & lượt xem)
CREATE TABLE IF NOT EXISTS public.publishing_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id TEXT UNIQUE NOT NULL,
    chapter_number INT NOT NULL,
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    telegram_reach INT DEFAULT 0,
    retention_rate NUMERIC DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. BANG CHARACTER_INVENTORY (Túi đồ, Pháp bảo & Dị Hỏa nhân vật)
CREATE TABLE IF NOT EXISTS public.character_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT DEFAULT 'Pháp Bảo',
    description TEXT,
    power_boost TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_character_item UNIQUE (novel_id, character_name, item_name)
);

-- 9. BANG AI_PROMPTS_LOG (Lịch sử nhật ký sinh ảnh AI & thẩm mỹ)
CREATE TABLE IF NOT EXISTS public.ai_prompts_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    engine_name TEXT DEFAULT 'Pollinations/Gemini',
    image_url TEXT,
    aesthetic_score NUMERIC DEFAULT 9.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. BANG TTS_VOICE_CONFIGS (Cấu hình giọng đọc AI & diễn cảm)
CREATE TABLE IF NOT EXISTS public.tts_voice_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    voice_name TEXT NOT NULL,
    pitch TEXT DEFAULT '+0Hz',
    rate TEXT DEFAULT '+0%',
    emotional_style TEXT DEFAULT 'epic',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_novel_character_voice UNIQUE (novel_id, character_name)
);

-- 11. BANG SYSTEM_LOGS (Nhật ký vận hành & cảnh báo tự động)
CREATE TABLE IF NOT EXISTS public.system_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level TEXT DEFAULT 'INFO',
    module_name TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. BANG CHANNEL_SUBSCRIBERS (Quản lý thành viên VIP & người hâm mộ)
CREATE TABLE IF NOT EXISTS public.channel_subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    platform TEXT DEFAULT 'Telegram',
    membership_level TEXT DEFAULT 'VIP Subscriber',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_platform UNIQUE (user_id, platform)
);

-- DISABLE RLS TO ALLOW FULL SERVICE ROLE AND ANON API ACCESS
ALTER TABLE public.novels DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.characters DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.world_lore DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.narrative_threads DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.chapters DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.episodes_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.publishing_analytics DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.character_inventory DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_prompts_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.tts_voice_configs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_subscribers DISABLE ROW LEVEL SECURITY;
