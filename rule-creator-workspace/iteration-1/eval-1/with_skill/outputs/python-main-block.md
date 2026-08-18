---
name: python-main-block
description: Ensure python scripts have an if __name__ == '__main__': block at the end
trigger: When creating or scaffolding a new Python script file
---

# Python Main Block

## Context
Luôn luôn thêm block `if __name__ == '__main__':` khi tạo file script Python để module vừa có thể chạy trực tiếp, vừa có thể được import an toàn mà không tự động thực thi các logic chính.

## Instructions
- Bất cứ khi nào tạo một file script Python, hãy tự động thêm đoạn mã sau vào cuối file:
  ```python
  if __name__ == '__main__':
      main() # hoặc logic thực thi tương ứng
  ```
- Nếu không có logic cụ thể nào để chạy lúc khởi tạo, có thể để `pass`.
