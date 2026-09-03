import sys

try:
    content = open('app.py', 'r', encoding='utf-8').read()
    old_msg = "Hệ thống vẫn đang vẽ ảnh (có thể mất 30 phút), vui lòng giữ tab này..."
    new_msg = "Hệ thống đang xử lý tác vụ nặng (vui lòng không đóng tab này)..."
    content = content.replace(old_msg, new_msg)
    open('app.py', 'w', encoding='utf-8').write(content)
    print('Patched app.py')
except Exception as e:
    print(f'Error: {e}')
