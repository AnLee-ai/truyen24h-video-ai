import sys

def fix_app_save():
    with open('templates/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_save = '''    document.getElementById('btn-api-save')?.addEventListener('click', (e) => {
        postSettings({
            'GEMINI_API_KEY': document.getElementById('env_GEMINI_API_KEY').value,
            'SUPABASE_URL': document.getElementById('env_SUPABASE_URL').value,
            'SUPABASE_KEY': document.getElementById('env_SUPABASE_KEY').value,
            'TELEGRAM_BOT_TOKEN': document.getElementById('env_TELEGRAM_BOT_TOKEN').value
        }, e.target);
    });'''
    
    new_save = '''    document.getElementById('btn-api-save')?.addEventListener('click', (e) => {
        postSettings({
            'GEMINI_API_KEY': document.getElementById('env_GEMINI_API_KEY').value,
            'GROQ_API_KEY': document.getElementById('env_GROQ_API_KEY') ? document.getElementById('env_GROQ_API_KEY').value : undefined,
            'SUPABASE_URL': document.getElementById('env_SUPABASE_URL').value,
            'SUPABASE_KEY': document.getElementById('env_SUPABASE_KEY').value,
            'TELEGRAM_BOT_TOKEN': document.getElementById('env_TELEGRAM_BOT_TOKEN').value,
            'TELEGRAM_CHAT_ID': document.getElementById('env_TELEGRAM_CHAT_ID') ? document.getElementById('env_TELEGRAM_CHAT_ID').value : undefined
        }, e.target);
    });'''
    
    content = content.replace(old_save, new_save)
    
    with open('templates/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
fix_app_save()
