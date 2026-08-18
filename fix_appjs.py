import sys
import re

with open('templates/app.js', encoding='utf-8') as f:
    content = f.read()

# 1. Elements
content = content.replace(
'''    const btnThumb = document.getElementById('btn-thumb');
    const inputNovelId = document.getElementById('novel-id');''',
'''    const btnThumb = document.getElementById('btn-thumb');
    const btnCancel = document.getElementById('btn-cancel');
    const inputNovelId = document.getElementById('novel-id');
    const autoScrollCheck = document.getElementById('auto-scroll');
    let currentEventSource = null;'''
)

# 2. appendLog
content = content.replace(
'''    function appendLog(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.textContent = message;
        consoleBody.appendChild(line);
        consoleBody.scrollTop = consoleBody.scrollHeight;
    }''',
'''    function appendLog(message, type = 'info') {
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
    }'''
)

# 3. setButtonsState
content = content.replace(
'''    function setButtonsState(disabled) {
        btnRun.disabled = disabled;
        btnThumb.disabled = disabled;
        inputNovelId.disabled = disabled;
    }''',
'''    function setButtonsState(disabled) {
        btnRun.disabled = disabled;
        btnThumb.disabled = disabled;
        inputNovelId.disabled = disabled;
        if (btnCancel) {
            btnCancel.style.display = disabled ? 'inline-block' : 'none';
        }
    }'''
)

# 4. connectSSE
content = content.replace(
'''        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {''',
'''        if (currentEventSource) currentEventSource.close();
        currentEventSource = new EventSource(url);

        currentEventSource.onmessage = (event) => {'''
)

content = content.replace(
'''            if (data.done) {
                eventSource.close();
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }''',
'''            if (data.done) {
                currentEventSource.close();
                currentEventSource = null;
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }'''
)

content = content.replace(
'''        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            eventSource.close();
            setButtonsState(false);
        };''',
'''        currentEventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            currentEventSource.close();
            currentEventSource = null;
            setButtonsState(false);
        };'''
)

# 5. Cancel Button Logic
content = content.replace(
'''    btnThumb.addEventListener('click', () => {
        connectSSE('run_thumbnail');
    });''',
'''    btnThumb.addEventListener('click', () => {
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
    }'''
)

with open('templates/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
