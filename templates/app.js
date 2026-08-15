document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabs = document.querySelectorAll('.content-body');
    const pageTitle = document.getElementById('page-title');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class
            navItems.forEach(nav => nav.classList.remove('active'));
            tabs.forEach(tab => tab.classList.add('hidden'));
            
            // Add active class
            item.classList.add('active');
            const tabId = item.getAttribute('data-tab');
            document.getElementById(`tab-${tabId}`).classList.remove('hidden');
            
            // Update title
            pageTitle.textContent = item.querySelector('span').textContent;
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
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.msg) {
                appendLog(data.msg, parseLogLine(data.msg));
            }
            if (data.done) {
                eventSource.close();
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            appendLog('[ERROR] Mất kết nối hoặc lỗi server.', 'error');
            eventSource.close();
            setButtonsState(false);
        };
    }

    btnRun.addEventListener('click', () => {
        connectSSE('run_pipeline');
    });

    btnThumb.addEventListener('click', () => {
        connectSSE('run_thumbnail');
    });
});
