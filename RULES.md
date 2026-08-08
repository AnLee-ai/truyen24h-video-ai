# 📜 QUY TẮC BẮT BUỘC: PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ & ĐÁNH GIÁ TÁC ĐỘNG BẢO VỆ HỆ THỐNG (ROOT CAUSE & IMPACT ASSESSMENT RULE)

---

## 1. 🔍 Phân Tích Nguyên Nhân Gốc Rễ (Deep Root Cause Analysis)
Mỗi khi có bất kỳ lỗi nào xuất hiện (Bug, Exception, Timeout, CSDL Duplicate, UI Mismatch,...), AI **BẮT BUỘC** phải tuân thủ quy trình 2 bước trước khi chạm vào mã nguồn:
- **1.1. Tìm Nguyên Nhân Cốt Lõi (Core Root Cause)**: Truy vết đến tận gốc rễ kiến trúc, luồng dữ liệu hoặc logic khởi tạo khiến lỗi phát sinh (Tuyệt đối không sửa ngọn hoặc vá víu triệu chứng).
- **1.2. Tìm Nguyên Nhân Xung Quanh (Surrounding Contributing Factors)**: Xác định tất cả các yếu tố môi trường/phụ trợ liên đới (Bộ nhớ đệm Cache, Format Payload, Ràng buộc CSDL, Giới hạn Telegram API, Cấu hình Socket).

---

## 2. ⚡ Đánh Giá Tác Động & Kiểm Tra Mâu Thuẫn (Impact & Conflict Assessment)
Trước khi đưa ra hoặc thực thi bất kỳ giải pháp sửa đổi nào, AI **BẮT BUỘC** phải thực hiện Đánh Giá Tác Động:
- **2.1. Kiểm Tra Mâu Thuẫn Kiến Trúc (Architectural Conflict Check)**: Thay đổi này có gây xung đột với bất kỳ module nào khác trong hệ thống không? (VD: `src/database.py`, `src/tts.py`, `src/video.py`, `src/telegram_uploader.py`).
- **2.2. Kiểm Tra Lỗi Dây Chuyền (Zero-Regression Downstream Check)**: Sửa đổi này có làm vỡ hoặc tạo ra lỗi mới ở các bước tiếp theo của Pipeline sản xuất Video/Audio không?
- **2.3. Kiểm Thử Xác Minh Bắt Buộc (Empirical Test Verification)**: Luôn chạy bộ test tích hợp toàn diện `python -m unittest tests/test_full_system_integrity.py` và kiểm tra `py_compile` để chứng minh 100% hệ thống hoạt động hoàn hảo không sinh ra lỗi mới.

---

## 3. 🎯 Mẫu Báo Cáo Chuẩn (Standard Resolution Output Format)
Mọi phản hồi xử lý lỗi phải bao gồm đủ 3 phần:
1. **Nguyên nhân cốt lõi & Các nguyên nhân xung quanh**.
2. **Đánh giá mâu thuẫn & Tác động dây chuyền (Bảo đảm 0 lỗi phát sinh)**.
3. **Kết quả kiểm thử thực nghiệm (Unit Test 100% Passed)**.
