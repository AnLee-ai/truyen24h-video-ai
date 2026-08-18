import sys

with open('templates/app.js', encoding='utf-8') as f:
    content = f.read()

target = '''    // Settings API logic
    async function fetchSettings() {
        try {
            const res = await fetch('/api/settings/get');
            const data = await res.json();
            if (data.status === 'success') {
                const map = {
                    'DEFAULT_VOICE': 'tts-voice-select',
                    'GEMINI_API_KEY': 'api-gemini',
                    'SUPABASE_URL': 'api-supabase-url',
                    'SUPABASE_KEY': 'api-supabase-key',
                    'TELEGRAM_BOT_TOKEN': 'api-telegram-token'
                };
                for (const [key, id] of Object.entries(map)) {
                    const el = document.getElementById(id);
                    if (el && data.data[key]) {
                        el.value = data.data[key];
                    }
                }
            }
        } catch (e) {
            console.error("Lỗi lấy cấu hình:", e);
        }
    }'''

replacement = '''    // Settings API logic
    async function fetchSettings() {
        try {
            const res = await fetch('/api/settings/get');
            const data = await res.json();
            if (data.status === 'success') {
                for (const [key, val] of Object.entries(data.data)) {
                    const el = document.getElementById('env_' + key);
                    if (el && val) el.value = val;
                }
                const ttsVoice = document.getElementById('tts-voice-select');
                if (ttsVoice && data.data['DEFAULT_VOICE']) ttsVoice.value = data.data['DEFAULT_VOICE'];
            }
        } catch (e) {
            console.error("Lỗi lấy cấu hình:", e);
        }
    }
    
    window.saveSettings = function(formId) {
        const form = document.getElementById(formId);
        if (!form) return;
        const payload = {};
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(i => {
            if (i.name) payload[i.name] = i.value;
        });
        const btn = form.querySelector('button[type="submit"]');
        postSettings(payload, btn);
    };'''

if target in content:
    content = content.replace(target, replacement)
    with open('templates/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("Could not find target!")
