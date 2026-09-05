document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabs = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class
            navItems.forEach(nav => nav.classList.remove('active'));
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Add active class
            item.classList.add('active');
            const tabId = item.getAttribute('data-tab');
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            // Update title
            pageTitle.textContent = item.textContent.trim();
        });
    });

    // Pipeline Logic
    const btnRun = document.getElementById('btn-run');
    const btnThumb = document.getElementById('btn-thumb');
    const inputNovelId = document.getElementById('novel-id');
    const consoleBody = document.getElementById('console');

    function appendLog(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.textContent = message;
        consoleBody.appendChild(line);
        consoleBody.scrollTop = consoleBody.scrollHeight;
    }

    function clearConsole() {
        consoleBody.innerHTML = '';
    }

    function setButtonsState(disabled) {
        btnRun.disabled = disabled;
        btnThumb.disabled = disabled;
        inputNovelId.disabled = disabled;
    }

    function parseLogLine(line) {
        if (line.includes('[ERROR]')) return 'error';
        if (line.includes('[SUCCESS]') || line.includes('✅')) return 'success';
        if (line.includes('[WARN]')) return 'warning';
        return 'info';
    }


// --- ANTI-SLEEP HACK ---
let wakeLock = null;
let audioCtx = null;
let oscillator = null;

async function keepTabAwake() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
        }
    } catch (err) {
        console.log('WakeLock failed:', err);
    }
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            await audioCtx.resume();
        }
        oscillator = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        gain.gain.value = 0.001;
        oscillator.connect(gain);
        gain.connect(audioCtx.destination);
        oscillator.start();
    } catch (err) {
        console.log('Audio API hack failed:', err);
    }
}

function releaseTabAwake() {
    if (wakeLock) {
        wakeLock.release().then(() => { wakeLock = null; }).catch(e => {});
    }
    if (oscillator) {
        oscillator.stop();
        oscillator.disconnect();
        oscillator = null;
    }
}

    function connectSSE(endpoint) {
        const novelId = inputNovelId.value.trim();
        if (!novelId) {
            appendLog('[ERROR] Vui lòng nhập Novel ID', 'error');
            return;
        }

        clearConsole();
        setButtonsState(true);
        keepTabAwake();
        appendLog(`[INFO] Đang kết nối tới ${endpoint}...`, 'info');

        const url = `/api/${endpoint}?novel_id=${encodeURIComponent(novelId)}`;
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.msg) {
                appendLog(data.msg, parseLogLine(data.msg));
            }
            if (data.done) {
                eventSource.close();
                releaseTabAwake();
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            eventSource.close();
            releaseTabAwake();
            setButtonsState(false);
        };
    }

    btnRun.addEventListener('click', () => {
        connectSSE('run_pipeline');
    });

    btnThumb.addEventListener('click', () => {
        connectSSE('run_thumbnail');
    });

    function escapeHTML(str) {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g, 
            tag => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[tag] || tag)
        );
    }

    // Data Fetching Logic
    async function fetchNovels() {
        const tbody = document.getElementById('novels-tbody');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Đang tải dữ liệu...</td></tr>';
        try {
            const res = await fetch('/api/novels');
            const data = await res.json();
            if (data.status === 'success') {
                if (data.data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Chưa có truyện nào đang chạy</td></tr>';
                    return;
                }
                tbody.innerHTML = data.data.map(n => `
                    <tr>
                        <td style="font-family: monospace; font-size: 0.8rem">${escapeHTML(n.id)}</td>
                        <td style="font-weight: 500">${escapeHTML(n.title || 'N/A')}</td>
                        <td><span class="badge-status badge-success">${escapeHTML(n.status)}</span></td>
                        <td>
                            <button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px;" onclick="document.getElementById('novel-id').value='${escapeHTML(n.id)}'; document.querySelector('.nav-item[data-tab=\\'pipeline\\']').click();">Chọn</button>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${escapeHTML(data.message || 'Lỗi không xác định')}</td></tr>`;
            }
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="color:red">Không thể kết nối đến server</td></tr>';
        }
    }

    async function fetchHistory() {
        const tbody = document.getElementById('history-tbody');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Đang tải dữ liệu...</td></tr>';
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            if (data.status === 'success') {
                if (data.data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Chưa có lịch sử video nào</td></tr>';
                    return;
                }
                tbody.innerHTML = data.data.map(c => {
                    const audioStatus = (c.audio_url || '').toLowerCase() === 'completed' || c.audio_url ? 'badge-success' : 'badge-warning';
                    const videoStatus = (c.video_status || '').toLowerCase() === 'completed' || c.video_url ? 'badge-success' : 'badge-secondary';
                    const audioText = c.audio_url ? 'Done' : 'Pending';
                    const videoText = (c.video_status || 'Pending').toUpperCase();
                    
                    const isAudioLink = c.audio_url && (c.audio_url.startsWith('http') || c.audio_url.startsWith('/'));
                    const audioContent = isAudioLink ? `<a href="${c.audio_url}" target="_blank" style="text-decoration:none; color:inherit;">${audioText} ↗</a>` : audioText;
                    const isVideoLink = c.video_url && (c.video_url.startsWith('http') || c.video_url.startsWith('/'));
                    const videoContent = isVideoLink ? `<a href="${c.video_url}" target="_blank" style="text-decoration:none; color:inherit;">${videoText} ↗</a>` : videoText;
                    
                    return `
                    <tr>
                        <td style="font-weight: 600">Chương ${escapeHTML(c.chapter_number)}</td>
                        <td>${escapeHTML(c.title || `Chương ${c.chapter_number}`)}</td>
                        <td><span class="badge-status ${audioStatus}">${audioContent}</span></td>
                        <td><span class="badge-status ${videoStatus}">${videoContent}</span></td>
                    </tr>
                `}).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${escapeHTML(data.message || 'Lỗi không xác định')}</td></tr>`;
            }
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="color:red">Không thể kết nối đến server</td></tr>';
        }
    }

    // Bind refresh buttons
    const btnRefNovels = document.getElementById('btn-refresh-novels');
    if (btnRefNovels) btnRefNovels.addEventListener('click', fetchNovels);
    
    const btnRefHistory = document.getElementById('btn-refresh-history');
    if (btnRefHistory) btnRefHistory.addEventListener('click', fetchHistory);

    // Initial fetch when clicking tabs
    document.querySelector('.nav-item[data-tab="novels"]').addEventListener('click', fetchNovels);
    document.querySelector('.nav-item[data-tab="history"]').addEventListener('click', fetchHistory);

    // Settings API logic
    async function fetchSettings() {
        try {
            const res = await fetch('/api/settings/get');
            const data = await res.json();
            if (data.status === 'success') {
                const map = {
                    'DEFAULT_VOICE': 'env_DEFAULT_VOICE',
                    'GEMINI_API_KEY': 'env_GEMINI_API_KEY',
                    'SUPABASE_URL': 'env_SUPABASE_URL',
                    'SUPABASE_KEY': 'env_SUPABASE_KEY',
                    'TELEGRAM_BOT_TOKEN': 'env_TELEGRAM_BOT_TOKEN',
                    'GROQ_API_KEY': 'env_GROQ_API_KEY',
                    'TELEGRAM_CHAT_ID': 'env_TELEGRAM_CHAT_ID',
                    'DEFAULT_RATE': 'env_DEFAULT_RATE',
                    'DEFAULT_PITCH': 'env_DEFAULT_PITCH'
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
    }

    // Custom Save logic
    async function postSettings(payload, btn) {
        const oldText = btn.textContent;
        btn.textContent = 'Đang lưu...';
        btn.disabled = true;
        try {
            const res = await fetch('/api/settings/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') alert('Lưu cấu hình thành công!');
            else alert('Lỗi: ' + data.message);
        } catch (e) {
            alert('Không thể kết nối đến server.');
        } finally {
            btn.textContent = oldText;
            btn.disabled = false;
        }
    }

    document.getElementById('btn-api-save')?.addEventListener('click', (e) => {
        postSettings({
            'GEMINI_API_KEY': document.getElementById('env_GEMINI_API_KEY').value,
            'GROQ_API_KEY': document.getElementById('env_GROQ_API_KEY') ? document.getElementById('env_GROQ_API_KEY').value : undefined,
            'SUPABASE_URL': document.getElementById('env_SUPABASE_URL').value,
            'SUPABASE_KEY': document.getElementById('env_SUPABASE_KEY').value,
            'TELEGRAM_BOT_TOKEN': document.getElementById('env_TELEGRAM_BOT_TOKEN').value,
            'TELEGRAM_CHAT_ID': document.getElementById('env_TELEGRAM_CHAT_ID') ? document.getElementById('env_TELEGRAM_CHAT_ID').value : undefined
        }, e.target);
    });

    document.getElementById('btn-tts-save')?.addEventListener('click', (e) => {
        postSettings({
            'DEFAULT_VOICE': document.getElementById('env_DEFAULT_VOICE').value,
            'DEFAULT_RATE': document.getElementById('env_DEFAULT_RATE') ? document.getElementById('env_DEFAULT_RATE').value : undefined,
            'DEFAULT_PITCH': document.getElementById('env_DEFAULT_PITCH') ? document.getElementById('env_DEFAULT_PITCH').value : undefined
        }, e.target);
    });

    // TTS Preview
    const btnPreview = document.getElementById('btn-tts-preview');
    const audioPlayer = document.getElementById('tts-audio-player');
    const audioContainer = document.getElementById('tts-audio-container');
    
    btnPreview?.addEventListener('click', async () => {
        const voice = document.getElementById('env_DEFAULT_VOICE').value;
        const text = document.getElementById('tts-preview-text').value;
        if(!text) return alert("Vui lòng nhập chữ để nghe thử!");
        
        const oldText = btnPreview.innerText;
        btnPreview.innerText = "Đang tạo audio...";
        btnPreview.disabled = true;
        
        try {
            const url = `/api/tts/preview?voice=${encodeURIComponent(voice)}&text=${encodeURIComponent(text)}`;
            const res = await fetch(url);
            if (res.ok) {
                const blob = await res.blob();
                if (audioPlayer.src) URL.revokeObjectURL(audioPlayer.src);
                const blobUrl = URL.createObjectURL(blob);
                audioPlayer.src = blobUrl;
                audioContainer.style.display = 'block';
                audioPlayer.play();
            } else {
                alert("Lỗi tạo audio!");
            }
        } catch(err) {
            alert("Lỗi mạng!");
        } finally {
            btnPreview.innerText = oldText;
            btnPreview.disabled = false;
        }
    });

    // Load initial settings
    fetchSettings();
});

