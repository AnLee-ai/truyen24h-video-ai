import os
import re
from src import config

class APIKeyRotator:
    """Quản lý xoay vòng đa tài khoản API Keys (Gemini, Groq) giúp nhân gấp N lần số Token & Quota miễn phí."""
    
    def __init__(self, provider: str, env_var_single: str, env_var_multi: str, default_keys: list = None):
        self.provider = provider
        self.keys = []
        
        # 1. Đọc từ biến môi trường phân cách bằng dấu phẩy, chấm phẩy hoặc xuống dòng
        multi_val = os.getenv(env_var_multi, "").strip()
        if multi_val:
            raw_tokens = re.split(r'[,;\n\r]+', multi_val)
            for k in raw_tokens:
                k_clean = k.strip().strip("'").strip('"')
                if k_clean and k_clean not in self.keys:
                    self.keys.append(k_clean)
                    
        # 2. Đọc các biến đánh số (VD: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
        idx = 1
        while True:
            k = os.getenv(f"{env_var_single}_{idx}", "").strip().strip("'").strip('"')
            if not k:
                break
            if k not in self.keys:
                self.keys.append(k)
            idx += 1
            
        # 3. Đọc biến đơn lẻ chuẩn (GEMINI_API_KEY / GROQ_API_KEY)
        single_val = os.getenv(env_var_single, "").strip().strip("'").strip('"')
        if single_val and single_val not in self.keys:
            self.keys.append(single_val)
            
        # 4. Sử dụng mặc định nếu có
        if not self.keys and default_keys:
            for d in default_keys:
                d_clean = d.strip().strip("'").strip('"') if isinstance(d, str) else ""
                if d_clean and d_clean not in self.keys:
                    self.keys.append(d_clean)
                    
        self.current_index = 0
        self.failed_keys = set()
        print(f"[INFO] API Key Rotator [{provider}]: Loaded {len(self.keys)} API Key account(s).")

    def get_key(self) -> str:
        """Lấy API key tiếp theo theo cơ chế Round-Robin."""
        valid_keys = [k for k in self.keys if k not in self.failed_keys]
        if not valid_keys:
            # Nếu tất cả key bị lỗi, reset danh sách để thử lại
            self.failed_keys.clear()
            valid_keys = self.keys

        if not valid_keys:
            return ""

        key = valid_keys[self.current_index % len(valid_keys)]
        self.current_index = (self.current_index + 1) % len(valid_keys)
        return key

    def mark_key_failed(self, key: str):
        """Đánh dấu key bị lỗi 401 hoặc 429 để tự động xoay sang tài khoản khác."""
        if key:
            key_mask = f"...{key[-6:]}" if len(key) >= 6 else key
            print(f"[WARNING] API Key [{self.provider}] {key_mask} bị hạn chế/lỗi. Đã tự động xoay sang tài khoản khác!")
            self.failed_keys.add(key)

# Khởi tạo hai bộ xoay vòng API Keys cho Gemini và Groq
gemini_rotator = APIKeyRotator(
    provider="Gemini",
    env_var_single="GEMINI_API_KEY",
    env_var_multi="GEMINI_API_KEYS"
)

groq_rotator = APIKeyRotator(
    provider="Groq",
    env_var_single="GROQ_API_KEY",
    env_var_multi="GROQ_API_KEYS"
)

def get_gemini_key() -> str:
    return gemini_rotator.get_key()

def get_groq_key() -> str:
    return groq_rotator.get_key()

def mark_gemini_key_failed(key: str):
    gemini_rotator.mark_key_failed(key)

def mark_groq_key_failed(key: str):
    groq_rotator.mark_key_failed(key)
