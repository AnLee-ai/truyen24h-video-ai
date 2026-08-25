file_path = r'd:\222\src\api\routers\pipelines.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''
                try:
                    msg = log_queue.get(timeout=0.1)
                    if "[ERROR]" in msg:
                        has_error = True
                    yield f"data: {json.dumps({'msg': msg})}\\n\\n"
                except queue.Empty:
                    await asyncio.sleep(0.1) # Yield control
'''

new_code = '''
                try:
                    msg = log_queue.get(timeout=1.0)
                    if "[ERROR]" in msg:
                        has_error = True
                    yield f"data: {json.dumps({'msg': msg})}\\n\\n"
                except queue.Empty:
                    yield ": heartbeat\\n\\n"
                    await asyncio.sleep(0.1)
'''

content = content.replace(old_code.strip('\n'), new_code.strip('\n'))

old_code2 = '''
            elif status["status"] == "failed":
                err = status.get('error', 'Unknown')
                yield f"data: {json.dumps({'msg': f'[ERROR] Lỗi: {err}', 'done': True})}\\n\\n"
                break
            await asyncio.sleep(1.0)
'''

new_code2 = '''
            elif status["status"] == "failed":
                err = status.get('error', 'Unknown')
                yield f"data: {json.dumps({'msg': f'[ERROR] Lỗi: {err}', 'done': True})}\\n\\n"
                break
            yield ": heartbeat\\n\\n"
            await asyncio.sleep(1.0)
'''

content = content.replace(old_code2.strip('\n'), new_code2.strip('\n'))

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
