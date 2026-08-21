import sys

def fix_app_js():
    with open('templates/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the old map
    old_map = '''                const map = {
                    'DEFAULT_VOICE': 'tts-voice-select',
                    'GEMINI_API_KEY': 'api-gemini',
                    'SUPABASE_URL': 'api-supabase-url',
                    'SUPABASE_KEY': 'api-supabase-key',
                    'TELEGRAM_BOT_TOKEN': 'api-telegram-token'
                };'''
                
    new_map = '''                const map = {
                    'DEFAULT_VOICE': 'env_DEFAULT_VOICE',
                    'GEMINI_API_KEY': 'env_GEMINI_API_KEY',
                    'SUPABASE_URL': 'env_SUPABASE_URL',
                    'SUPABASE_KEY': 'env_SUPABASE_KEY',
                    'TELEGRAM_BOT_TOKEN': 'env_TELEGRAM_BOT_TOKEN',
                    'GROQ_API_KEY': 'env_GROQ_API_KEY',
                    'TELEGRAM_CHAT_ID': 'env_TELEGRAM_CHAT_ID',
                    'DEFAULT_RATE': 'env_DEFAULT_RATE',
                    'DEFAULT_PITCH': 'env_DEFAULT_PITCH'
                };'''
                
    content = content.replace(old_map, new_map)
    
    with open('templates/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
fix_app_js()
