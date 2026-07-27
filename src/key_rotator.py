import os
import random
from src import config

class APIKeyRotator:
    """Quản lý xoay vòng đa tài khoản API Keys (Gemini, Groq) giúp nhân gấp N lần số Token & Quota miễn phí."""
    
    def __init__(self, provider: str, env_var_single: str, env_var_multi: str, default_keys: list = None):
        self.provider = provider
        self.keys = []
        
        # 1. Đọc từ biến môi trường dạng danh sách phân cách dấu phẩy (VD: GEMINI_API_KEYS=key1,key2,key3)
        multi_val = os.getenv(env_var_multi, "").strip()
        if multi_val:
            for k in multi_val.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in self.keys:
                    self.keys.append(k_clean)
                    
        # 2. Đọc các biến đánh số (VD: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
        idx = 1
        while True:
            k = os.getenv(f"{env_var_single}_{idx}", "").strip()
            if not k:
                break
            if k not in self.keys:
                self.keys.append(k)
            idx += 1
            
        # 3. Đọc biến đơn lẻ chuẩn
        single_val = os.getenv(env_var_single, "").strip()
        if single_val and single_val not in self.keys:
            self.keys.append(single_val)
            
        # 4. Sử dụng mặc định nếu có
        if not self.keys and default_keys:
            for d in default_keys:
                if d and d not in self.keys:
                    self.keys.append(d)
                    
        self.current_index = 0
        self.failed_keys = set()
        print(f"[INFO] API Key Rotator [{provider}]: Loaded {len(self.keys)} API Key account(s).")

    def get_key(self) -> str:
        """Lấy API key tiếp theo theo cơ chế Round-Robin."""
        valid_keys = [k for k in self.keys if k not in self.failed_keys]
        if not valid_keys:
            # Reset danh sách lỗi nếu tất cả khóa đều bị giới hạn tạm thời
            self.failed_keys.clear()
            valid_keys = self.keys

        if not valid_keys:
            return ""

        key = valid_keys[self.current_index % len(valid_keys)]
        self.current_index = (self.current_index + 1) % len(valid_keys)
        return key

    def mark_key_failed(self, key: str):
        """Đánh dấu key bị hạn chế Quota (429 Rate Limit) để chuyển sang key tài khoản khác."""
        if key and len(self.keys) > 1:
            print(f"[WARNING] API Key [{self.provider}] ...{key[-6:]} bị giới hạn Quota. Đã tự động xoay sang tài khoản khác!")
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
    env_var_multi="GROQ_API_KEYS",
    default_keys=[config.GROQ_API_KEY] if getattr(config, "GROQ_API_KEY", None) else []
)

def get_gemini_key() -> str:
    return gemini_rotator.get_key()

def get_groq_key() -> str:
    return groq_rotator.get_key()

def mark_gemini_key_failed(key: str):
    gemini_rotator.mark_key_failed(key)

def mark_groq_key_failed(key: str):
    groq_rotator.mark_key_failed(key)
