import sys

with open('templates/index.html', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
'''                            <div class="action-buttons">
                                <button id="btn-run" class="btn btn-primary">Viết Chương & Video</button>
                                <button id="btn-thumb" class="btn btn-outline">Chỉ Tạo Thumbnail</button>
                            </div>''',
'''                            <div class="action-buttons">
                                <button id="btn-run" class="btn btn-primary">Viết Chương & Video</button>
                                <button id="btn-thumb" class="btn btn-outline">Chỉ Tạo Thumbnail</button>
                                <button id="btn-cancel" class="btn btn-danger" style="display: none; background: #dc3545; color: white; border: none;">Hủy</button>
                            </div>'''
)

content = content.replace(
'''                                <div class="status-header">
                                    <h3>Trạng Thái Sinh Video</h3>
                                    <span class="badge">Live Logs</span>
                                </div>''',
'''                                <div class="status-header" style="display: flex; justify-content: space-between; align-items: center;">
                                    <h3 style="margin: 0;">Trạng Thái Sinh Video</h3>
                                    <div style="display: flex; gap: 10px; align-items: center;">
                                        <label style="font-size: 0.8rem; display: flex; align-items: center; gap: 5px; cursor: pointer; color: #a0aec0;">
                                            <input type="checkbox" id="auto-scroll" checked> Auto-scroll
                                        </label>
                                        <span class="badge">Live Logs</span>
                                    </div>
                                </div>'''
)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
