import os, requests

def upload_to_gofile(file_path):
    print(f'[INFO] Thử upload {file_path} lên GoFile...')
    try:
        # 1. Lấy server tốt nhất
        servers_res = requests.get('https://api.gofile.io/servers').json()
        if servers_res['status'] != 'ok':
            print('[ERROR] GoFile server error')
            return ''
        server = servers_res['data']['servers'][0]['name']
        
        # 2. Upload file
        url = f'https://{server}.gofile.io/contents/uploadfile'
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            res = requests.post(url, files=files).json()
            if res['status'] == 'ok':
                download_page = res['data']['downloadPage']
                direct_link = download_page
                print(f'[SUCCESS] GoFile Upload thành công: {direct_link}')
                return direct_link
    except Exception as e:
        print(f'[ERROR] GoFile Upload thất bại: {e}')
    return ''

print('GoFile Test Script Created')
