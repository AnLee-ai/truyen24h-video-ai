import sys

def fix_app_save_tts():
    with open('templates/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_save = '''    document.getElementById('btn-tts-save')?.addEventListener('click', (e) => {
        postSettings({
            'DEFAULT_VOICE': document.getElementById('env_DEFAULT_VOICE').value
        }, e.target);
    });'''
    
    new_save = '''    document.getElementById('btn-tts-save')?.addEventListener('click', (e) => {
        postSettings({
            'DEFAULT_VOICE': document.getElementById('env_DEFAULT_VOICE').value,
            'DEFAULT_RATE': document.getElementById('env_DEFAULT_RATE') ? document.getElementById('env_DEFAULT_RATE').value : undefined,
            'DEFAULT_PITCH': document.getElementById('env_DEFAULT_PITCH') ? document.getElementById('env_DEFAULT_PITCH').value : undefined
        }, e.target);
    });'''
    
    content = content.replace(old_save, new_save)
    
    with open('templates/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
fix_app_save_tts()
