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
    const btnCancel = document.getElementById('btn-cancel');
    const inputNovelId = document.getElementById('novel-id');
    const autoScrollCheck = document.getElementById('auto-scroll');
    let currentEventSource = null;
    const consoleBody = document.getElementById('console');

    function appendLog(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        // Color coding
        let color = '#e2e8f0'; // default text-muted
        if (type === 'error') color = '#fc8181';
        else if (type === 'success') color = '#68d391';
        else if (type === 'warning') color = '#f6ad55';
        else if (message.includes('[INFO]')) color = '#63b3ed';
        
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        
        line.innerHTML = `<span style="color: #718096; margin-right: 8px;">[${timeStr}]</span><span style="color: ${color}">${escapeHTML(message)}</span>`;
        consoleBody.appendChild(line);
        
        if (autoScrollCheck && autoScrollCheck.checked) {
            consoleBody.scrollTop = consoleBody.scrollHeight;
        }
    }

    function clearConsole() {
        consoleBody.innerHTML = '';
    }

    function setButtonsState(disabled) {
        btnRun.disabled = disabled;
        btnThumb.disabled = disabled;
        inputNovelId.disabled = disabled;
        if (btnCancel) {
            btnCancel.style.display = disabled ? 'inline-block' : 'none';
        }
    }

    function parseLogLine(line) {
        if (line.includes('[ERROR]')) return 'error';
        if (line.includes('[SUCCESS]') || line.includes('✅')) return 'success';
        if (line.includes('[WARN]')) return 'warning';
        return 'info';
    }

    function connectSSE(endpoint) {
        const novelId = inputNovelId.value.trim();
        if (!novelId) {
            appendLog('[ERROR] Vui lòng nhập Novel ID', 'error');
            return;
        }

        clearConsole();
        setButtonsState(true);
        appendLog(`[INFO] Đang kết nối tới ${endpoint}...`, 'info');

        const url = `/api/${endpoint}?novel_id=${encodeURIComponent(novelId)}`;
        if (currentEventSource) currentEventSource.close();
        currentEventSource = new EventSource(url);

        currentEventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.msg) {
                appendLog(data.msg, parseLogLine(data.msg));
            }
            if (data.done) {
                currentEventSource.close();
                currentEventSource = null;
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }
        };

        currentEventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            currentEventSource.close();
            currentEventSource = null;
            setButtonsState(false);
        };
    }

    btnRun.addEventListener('click', () => {
        connectSSE('run_pipeline');
    });

    btnThumb.addEventListener('click', () => {
        connectSSE('run_thumbnail');
    });

    if (btnCancel) {
        btnCancel.addEventListener('click', async () => {
            const novelId = inputNovelId.value.trim();
            if (!novelId) return;
            
            btnCancel.disabled = true;
            btnCancel.textContent = 'Đang hủy...';
            
            try {
                const res = await fetch(`/api/cancel_pipeline?novel_id=${encodeURIComponent(novelId)}`);
                const data = await res.json();
                appendLog(`[WARN] ${data.message}`, 'warning');
            } catch(e) {
                appendLog('[ERROR] Lỗi khi hủy tiến trình.', 'error');
            } finally {
                btnCancel.disabled = false;
                btnCancel.textContent = 'Hủy';
                if (currentEventSource) {
                    currentEventSource.close();
                    currentEventSource = null;
                }
                setButtonsState(false);
            }
        });
    }

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
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${data.message}</td></tr>`;
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
                    
                    return `
                    <tr>
                        <td style="font-weight: 600">Chương ${escapeHTML(c.chapter_number)}</td>
                        <td>${escapeHTML(c.title || `Chương ${c.chapter_number}`)}</td>
                        <td><span class="badge-status ${audioStatus}">${audioText}</span></td>
                        <td><span class="badge-status ${videoStatus}">${videoText}</span></td>
                    </tr>
                `}).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${data.message}</td></tr>`;
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
    };

    // Custom Save logic
    async function postSettings(payload, btn) {
        const oldText = btn.textContent;
        const oldBg = btn.style.backgroundColor;
        btn.textContent = 'Đang lưu...';
        btn.disabled = true;
        try {
            const res = await fetch('/api/settings/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                btn.textContent = '✅ Đã lưu thành công!';
                btn.style.backgroundColor = '#48bb78';
                setTimeout(() => {
                    btn.textContent = oldText;
                    btn.style.backgroundColor = oldBg;
                    btn.disabled = false;
                }, 2000);
                return;
            } else {
                alert('Lỗi: ' + data.message);
            }
        } catch (e) {
            alert('Không thể kết nối đến server.');
        }
        btn.textContent = oldText;
        btn.disabled = false;
    }

    document.getElementById('btn-api-save')?.addEventListener('click', (e) => {
        postSettings({
            'GEMINI_API_KEY': document.getElementById('api-gemini').value,
            'SUPABASE_URL': document.getElementById('api-supabase-url').value,
            'SUPABASE_KEY': document.getElementById('api-supabase-key').value,
            'TELEGRAM_BOT_TOKEN': document.getElementById('api-telegram-token').value
        }, e.target);
    });

    document.getElementById('btn-tts-save')?.addEventListener('click', (e) => {
        postSettings({
            'DEFAULT_VOICE': document.getElementById('tts-voice-select').value
        }, e.target);
    });

    // TTS Preview
    const btnPreview = document.getElementById('btn-tts-preview');
    const audioPlayer = document.getElementById('tts-audio-player');
    const audioContainer = document.getElementById('tts-audio-container');
    
    btnPreview?.addEventListener('click', async () => {
        const voice = document.getElementById('tts-voice-select').value;
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

