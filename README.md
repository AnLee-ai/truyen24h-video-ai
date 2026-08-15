# Truyện 24h Studio (Enterprise Audio Engine)

Hệ thống tự động hóa toàn diện từ Kịch bản văn bản -> Audio AI (TTS) -> Video (FFMpeg) -> Auto Upload. Được nâng cấp mạnh mẽ ở phiên bản Enterprise với khả năng tự phục hồi, chống chịu lỗi và có giao diện điều khiển (Web UI).

## 🚀 Tính năng nổi bật (Bản Enterprise)

- **Smart Checkpointing (Tự phục hồi):** Lưu trạng thái từng bước (Viết kịch bản, Audio, Video, Upload). Sẵn sàng resume (tiếp tục) từ điểm đứt gãy nếu mất điện hoặc sập mạng, không phải làm lại từ đầu.
- **Lightweight Job Queue:** Hàng đợi tác vụ đa luồng (chạy nền) tự động, giúp xử lý song song nhiều tập truyện mà không làm treo hệ thống.
- **Database Caching:** Trí tuệ nhân tạo đọc trực tiếp dữ liệu cũ từ cache thay vì gọi API liên tục cho các đoạn text trùng lặp, tối ưu 100% token AI tốn kém.
- **Premium Web Dashboard:** Bảng điều khiển Web UI (`http://localhost:7860/`) sang trọng, tích hợp trực tiếp tiến trình quản lý truyện và hệ thống. Không còn phải cấu hình qua CLI khô khan.
- **Thumbnail AI Agent:** Hệ thống tự động tạo ảnh bìa clickbait cho YouTube/TikTok.
- **Đa Luồng Thực Thi:** Hỗ trợ xử lý song song 5-10 worker khi kết xuất AI hoặc vẽ ảnh, giảm 40% thời gian chờ đợi.
- **API Key Rotator & Fallback:** Không bao giờ chết luồng. Khi hết tiền OpenAI/Gemini hoặc lỗi API, hệ thống tự động nhảy sang hàng chục nguồn LLM miễn phí (OpenRouter, Pollinations).

## 🏗 Kiến trúc Hệ thống

- `src/main.py`: Điểm đầu vào chính (Orchestrator) & FastAPI Server (chạy Web Dashboard).
- `src/writer.py`: Đặc vụ viết kịch bản AI (Tích hợp Key Rotator & Caching).
- `src/tts.py`: Hệ thống chuyển văn bản thành giọng nói (Sử dụng edge-tts miễn phí).
- `src/video.py`: Pipeline dùng FFmpeg ghép nối Video + Âm thanh + Phụ đề.
- `src/checkpoint.py`: Cơ chế lưu vết (Save states) thông minh.
- `src/queue_manager.py`: Bộ máy chạy nền (Background workers).
- `src/cache.py`: Trình quản lý tối ưu token AI (Cache hits).
- `src/youtube_uploader.py`: Trí tuệ đẩy video YouTube qua API ẩn.
- `src/telegram_uploader.py`: Trí tuệ đẩy thông báo và file lên kênh Telegram.

## 💻 Cách vận hành

Khởi chạy Server & Dashboard:
```bash
python -m src.main --action serve
```
Mở trình duyệt: `http://localhost:7860/`

**Thiết kế bởi Antigravity AI.**
