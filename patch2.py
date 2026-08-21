import sys, os, re

sys.stdout.reconfigure(encoding='utf-8')

def patch(filename, old, new):
    if not os.path.exists(filename): return
    content = open(filename, 'r', encoding='utf-8').read()
    if old in content:
        content = content.replace(old, new)
        open(filename, 'w', encoding='utf-8').write(content)
        print(f'Patched {filename}')
    else:
        print(f'Failed to patch {filename} - old text not found')

# 1. main.py - top level import json
patch('src/main.py', 'import argparse\nimport sys', 'import argparse\nimport json\nimport sys')

# 2. main.py - Guard after write_next_chapter
old_guard1 = '''            chapter = writer.write_next_chapter(novel_id)
            chapter_id = chapter["id"]'''
new_guard1 = '''            chapter = writer.write_next_chapter(novel_id)
            if not chapter or "id" not in chapter:
                if log_callback: log_callback("[ERROR] Không thể viết chương mới.")
                return
            chapter_id = chapter["id"]'''
patch('src/main.py', old_guard1, new_guard1)

# 3. main.py - Guard audio paths
old_guard2 = '''            raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter_content, chapter_id)
            
            # Mix speech audio with background music
            final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
            
            # Đo chính xác'''
new_guard2 = '''            raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter_content, chapter_id)
            if not raw_audio_path:
                if log_callback: log_callback("[ERROR] TTS thất bại.")
                return
            
            # Mix speech audio with background music
            final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
            if not final_audio_path:
                if log_callback: log_callback("[ERROR] Mix audio thất bại.")
                return
                
            # Đo chính xác'''
patch('src/main.py', old_guard2, new_guard2)

# 4. writer.py - novel_id
patch('src/writer.py', 'novel_id = novel["id"]', 'novel_id = novel.get("id") or "";\n    if not novel_id: raise ValueError("init_novel failed")')

# 5. writer.py - chapter_record content
patch('src/writer.py', 'blueprint_text = chapter_record["content"]', 'blueprint_text = (chapter_record or {}).get("content", "BLUEPRINT: default")')

# 6. writer.py - protagonist getters
patch('src/writer.py', 'protagonist_name = protagonist["name"] if protagonist else "Jack"', 'protagonist_name = protagonist.get("name", "Jack") if protagonist else "Jack"')
patch('src/writer.py', 'protagonist_power = protagonist["power_tier"] if protagonist else "Ordinary"', 'protagonist_power = protagonist.get("power_tier", "Ordinary") if protagonist else "Ordinary"')
patch('src/writer.py', 'protagonist_stats = json.dumps(protagonist["combat_stats"]) if protagonist else "{}"', 'protagonist_stats = json.dumps(protagonist.get("combat_stats", {})) if protagonist else "{}"')
patch('src/writer.py', 'failure_flag = protagonist["failure_flag"] if protagonist else False', 'failure_flag = protagonist.get("failure_flag", False) if protagonist else False')
patch('src/writer.py', 'last_breakthrough_ch = protagonist["last_breakthrough_chapter"] if protagonist else 0', 'last_breakthrough_ch = protagonist.get("last_breakthrough_chapter", 0) if protagonist else 0')

# 7. settings.py - Pydantic model
old_settings = '''class SettingsUpdate(BaseModel):
    GEMINI_API_KEY: str = None
    SUPABASE_URL: str = None'''
new_settings = '''class SettingsUpdate(BaseModel):
    GEMINI_API_KEY: str = None
    GROQ_API_KEY: str = None
    SUPABASE_URL: str = None'''
patch('src/api/routers/settings.py', old_settings, new_settings)

old_settings_tts = '''    DISCORD_WEBHOOK_URL: str = None
    DEFAULT_VOICE: str = None'''
new_settings_tts = '''    DISCORD_WEBHOOK_URL: str = None
    DEFAULT_VOICE: str = None
    DEFAULT_RATE: str = None
    DEFAULT_PITCH: str = None'''
patch('src/api/routers/settings.py', old_settings_tts, new_settings_tts)

# 8. app.js - ids
patch('templates/app.js', "document.getElementById('api-gemini')", "document.getElementById('env_GEMINI_API_KEY')")
patch('templates/app.js', "document.getElementById('api-supabase-url')", "document.getElementById('env_SUPABASE_URL')")
patch('templates/app.js', "document.getElementById('api-supabase-key')", "document.getElementById('env_SUPABASE_KEY')")
patch('templates/app.js', "document.getElementById('api-telegram-token')", "document.getElementById('env_TELEGRAM_BOT_TOKEN')")
patch('templates/app.js', "document.getElementById('tts-voice-select')", "document.getElementById('env_DEFAULT_VOICE')")

print('Patching complete!')
