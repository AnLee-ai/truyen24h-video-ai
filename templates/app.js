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

    // Toast Notification System
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || (function() {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
            document.body.appendChild(container);
            return container;
        })();

        const toast = document.createElement('div');
        const bgColors = {
            'success': '#10b981',
            'error': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        };
        toast.style.cssText = `background: ${bgColors[type] || bgColors['info']}; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-weight: 500; font-size: 14px; opacity: 0; transform: translateY(20px); transition: all 0.3s ease;`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });

        // Animate out after 3s
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // WebSocket Global Connection
    let ws = null;
    function connectWS() {
        if (ws && ws.readyState !== WebSocket.CLOSED) return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress`);
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'log' && data.msg) {
                    appendLog(data.msg, parseLogLine(data.msg));
                } else if (data.type === 'status') {
                    if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
                        setButtonsState(false);
                        const btnStop = document.getElementById('btn-stop');
                        if (btnStop) btnStop.style.display = 'none';
                        appendLog(`[INFO] Task ${data.task_id} kết thúc với trạng thái: ${data.status}`, data.status === 'failed' ? 'error' : 'success');
                    }
                }
            } catch(e) {}
        };
        
        ws.onclose = () => {
            console.log("WebSocket disconnected. Reconnecting in 3s...");
            setTimeout(connectWS, 3000);
        };
    }
    
    // Khởi tạo WS khi load trang
    connectWS();

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

    let currentTaskId = null;
    const btnStop = document.getElementById('btn-stop');

    async function triggerTask(endpoint) {
        const novelId = inputNovelId.value.trim();
        if (!novelId) {
            showToast('Vui lòng nhập Novel ID', 'error');
            return;
        }

        clearConsole();
        setButtonsState(true);
        btnStop.style.display = 'block';
        appendLog(`[INFO] Gửi yêu cầu tới ${endpoint}...`, 'info');

        try {
            const res = await fetch(`/api/${endpoint}?novel_id=${encodeURIComponent(novelId)}`);
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'success');
                appendLog(`[INFO] ${data.message}`, 'info');
                currentTaskId = data.task_id;
            } else {
                showToast(data.message, 'error');
                appendLog(`[ERROR] ${data.message}`, 'error');
                setButtonsState(false);
                btnStop.style.display = 'none';
            }
        } catch (e) {
            showToast('Không thể kết nối đến server', 'error');
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            setButtonsState(false);
            btnStop.style.display = 'none';
        }
    }

    btnStop.addEventListener('click', async () => {
        if (!currentTaskId) return;
        const oldText = btnStop.textContent;
        btnStop.textContent = 'Đang huỷ...';
        btnStop.disabled = true;
        
        try {
            const res = await fetch(`/api/cancel_task?task_id=${encodeURIComponent(currentTaskId)}`);
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'info');
            } else {
                showToast(data.message, 'error');
            }
        } catch (e) {
            showToast('Không thể kết nối đến server', 'error');
        } finally {
            btnStop.textContent = oldText;
            btnStop.disabled = false;
        }
    });

    // Cập nhật lại logic WS để ẩn nút Stop
    // Tôi sẽ cập nhật hàm connectWS sau.
    btnRun.addEventListener('click', () => triggerTask('run_pipeline'));
    btnThumb.addEventListener('click', () => triggerTask('run_thumbnail'));

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

    // System Settings (Theme & Cache)
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        const savedTheme = localStorage.getItem('app-theme') || 'light';
        themeSelect.value = savedTheme;
        if (savedTheme === 'dark') document.body.classList.add('dark-mode');
        
        themeSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            localStorage.setItem('app-theme', val);
            if (val === 'dark') document.body.classList.add('dark-mode');
            else document.body.classList.remove('dark-mode');
        });
    }

    const btnCleanCache = document.getElementById('btn-clean-cache');
    if (btnCleanCache) {
        btnCleanCache.addEventListener('click', async () => {
            if (!confirm('Bạn có chắc muốn xoá toàn bộ cache rác trong thư mục output không? Việc này không thể hoàn tác!')) return;
            const oldText = btnCleanCache.textContent;
            btnCleanCache.textContent = 'Đang dọn dẹp...';
            btnCleanCache.disabled = true;
            try {
                const res = await fetch('/api/settings/clean_cache', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') alert('Đã dọn dẹp xong!');
                else alert('Lỗi: ' + data.message);
            } catch (e) {
                alert('Không thể kết nối đến server.');
            } finally {
                btnCleanCache.textContent = oldText;
                btnCleanCache.disabled = false;
            }
        });
    }

    // Load initial settings
    fetchSettings();
    // Khởi tạo Chart.js (Analytics)
    const ctx = document.getElementById('analyticsChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'],
                datasets: [{
                    label: 'Số Video Sinh Ra',
                    data: [1, 3, 2, 5, 4, 7, 6],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 2 }
                    }
                }
            }
        });
    }

});

