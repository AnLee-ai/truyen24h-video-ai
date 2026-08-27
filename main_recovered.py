Created At: 2026-08-17T14:36:21+07:00
Completed At: 2026-08-17T14:36:21+07:00
File Path: `file:///d:/222/src/main.py`
Total Lines: 495
Total Bytes: 26237
Showing lines 1 to 495
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
1: import argparse
2: import sys
3: from src import checkpoint
4: import os
5: import contextlib
6: import uvicorn
7: from fastapi import FastAPI, BackgroundTasks, Request
8: from fastapi.responses import HTMLResponse
9: from fastapi.templating import Jinja2Templates
10: from fastapi.staticfiles import StaticFiles
11: 
12: from src import config
13: from src import database
14: from src import writer
15: from src import tts
16: from src import audio
17: from src import telegram_uploader
18: from src import video
19: from src import thumbnail_generator
20: from src import checkpoint
21: from src.queue_manager import job_queue
22: 
23: def safe_print(*args, **kwargs):
24:     """Safely print message preventing UnicodeEncodeError on Windows terminals."""
25:     msg = " ".join(str(arg) for arg in args)
26:     try:
27:         sys.stdout.write(msg + kwargs.get("end", "\n"))
28:         sys.stdout.flush()
29:     except UnicodeEncodeError:
30:         try:
31:             encoding = sys.stdout.encoding or 'utf-8'
32:             sys.stdout.write(msg.encode(encoding, errors='replace').decode(encoding) + kwargs.get("end", "\n"))
33:             sys.stdout.flush()
34:         except Exception:
35:             sys.stdout.write(msg.encode('ascii', errors='replace').decode('ascii') + kwargs.get("end", "\n"))
36:             sys.stdout.flush()
37: 
38: print = safe_print
39: 
40: # Initialize FastAPI App
41: app = FastAPI(title="Truyện 24h Audio Engine", version="1.0.0")
42: templates = Jinja2Templates(directory="src/templates")
43: import os
44: app.mount("/static", StaticFiles(directory="templates"), name="static")
45: 
46: 
47: class CallbackStream:
48:     def __init__(self, original_stream, callback):
49:         self.original_stream = original_stream
50:         self.callback = callback
51:         
52:     def write(self, data):
53:         self.original_stream.write(data)
54:         if data.strip():
55:             self.callback(data.strip())
56:             
57:     def flush(self):
58:         self.original_stream.flush()
59: 
60: def audit_chapter_quality(ch: dict) -> tuple:
61:     """
62:     BỘ BẢO VỆ & RÀ SOÁT TIÊU CHUẨN TỰ ĐỘNG (Quality Auditor Engine):
63:     Rà soát Tiêu chuẩn chất lượng cho mỗi chương truyện:
64:     1. Kịch bản văn bản đầy đủ ≥ 1,000 từ (chuẩn audio > 10 phút).
65:     2. Không chứa tên nhân vật cũ rác (Trần Lam, Linh Vy, Minh Đức).
66:     """
67:     ch_num = ch.get("chapter_number", 0)
68:     ch_content = str(ch.get("content", ""))
69:     word_count = len(ch_content.split()) if ch_content else 0
70:     
71:     # 1. Tiêu chuẩn 1: Kịch bản text ngắn (<1000 từ) hoặc còn là BLUEPRINT
72:     if not ch_content or ch_content.startswith("BLUEPRINT:") or word_count < 1000:
73:         return False, f"Chương {ch_num}: Kịch bản quá ngắn ({word_count} từ < 1000 từ tiêu chuẩn)"
74:         
75:     # 2. Tiêu chuẩn 2: Chứa tên nhân vật rác cũ
76:     for old_name in ["Trần Lam", "Linh Vy", "Minh Đức", "Thùy Linh", "Cao Bá"]:
77:         if old_name in ch_content:
78:             return False, f"Kịch bản chứa tên nhân vật cũ rác '{old_name}'"
79:             
80:     return True, "PASSED"
81: 
82: def find_chapter_needing_video(novel_id: str) -> dict:
83:     """
84:     TỰ ĐỘNG PHÁT HIỆN TẬP CHƯA XỬ LÝ (CHỐNG LẶP CHƯƠNG 100%):
85:     1. Lấy danh sách 100% tập ĐÃ XONG từ Supabase + data/ + output/ + RAM.
86:     2. Nếu Tập ch_num đã nằm trong completed_set -> BỎ QUA HOÀN TOÀN.
87:     3. Trả về tập đầu tiên thực sự chưa hoàn thành.
88:     """
89:     completed_set = database.get_completed_chapters_set(novel_id)
90: 
91:     try:
92:         all_chapters = database.get_all_chapters(novel_id)
93:         for ch in all_chapters:
94:             ch_id = str(ch.get("id", ""))
95:             ch_num = int(ch.get("chapter_number", 0)) if str(ch.get("chapter_number", "")).isdigit() else 0
96:             
97:             # Kiểm tra xem Tập ch_num đã xong Media chưa
98:             is_done = (ch_num in completed_set) or (str(ch_num) in completed_set) or (ch_id in completed_set)
99:             
100:             if is_done:
101:                 print(f"[QUALITY AUDITOR] 🟢 Tập {ch_num} (ID: {ch_id}) ĐÃ HOÀN THÀNH MEDIA. Bỏ qua hoàn toàn để làm tập tiếp theo!")
102:                 continue
103: 
104:             # Rà soát kịch bản của Tập ch_num chưa hoàn thành
105:             passed, reason = audit_chapter_quality(ch)
106:             if not passed:
107:                 print(f"[QUALITY AUDITOR] ⚠️ TẬP {ch_num} (ID: {ch_id}) KHÔNG ĐẠT TIÊU CHUẨN KỊCH BẢN ({reason}). Dành cho writer.write_next_chapter viết mới đủ 2500+ từ!")
108:                 continue
109:                 
110:             print(f"[QUALITY AUDITOR] 🎯 PHÁT HIỆN TẬP CHƯA XONG MEDIA: Tập {ch_num} (ID: {ch_id}). Tiến hành sản xuất Video!")
111:             return ch
112:             
113:     except Exception as e:
114:         print(f"[WARNING] Lỗi quét kiểm tra tiêu chuẩn chất lượng: {e}")
115:         
116:     return {}
117: 
118: def run_chapter_pipeline(novel_id: str, log_callback=None):
119:     """Executes the full pipeline for writing a chapter and uploading audio."""
120:     if log_callback:
121:         stream = CallbackStream(sys.stdout, log_callback)
122:         with contextlib.redirect_stdout(stream):
123:             _run_chapter_pipeline_impl(novel_id)
124:     else:
125:         _run_chapter_pipeline_impl(novel_id)
126: 
127: def _run_chapter_pipeline_impl(novel_id: str):
128:     """Internal implementation of the pipeline."""
129:     if not config.validate_config():
130:         print("[ERROR] Configuration validation failed. Aborting pipeline.")
131:         return
132:         
133:     try:
134:         # 0. TỰ ĐỘNG PHÁT HIỆN CHƯƠNG ĐÃ CÓ AUDIO NHƯNG CHƯA CÓ VIDEO (ƯU TIÊN RENDER VIDEO NGAY)
135:         pending_video_ch = find_chapter_needing_video(novel_id)
136:         is_resuming_video = False
137:         if pending_video_ch:
138:             chapter = pending_video_ch
139:             chapter_id = chapter["id"]
140:             chapter_num = chapter["chapter_number"]
141:             chapter_title = chapter["title"]
142:             chapter_content = chapter["content"]
143:             is_resuming_video = True
144:             print(f"[INFO] TRỰC TIẾP BỎ QUA BƯỚC VIẾT CHƯƠNG MỚI! Tập trung render Video ngay cho Chương {chapter_num}: '{chapter_title}' (Words: {len(chapter_content.split())})...")
145:         else:
146:             # 1. Viết chương tiếp theo nếu tất cả các chương cũ đã có video đầy đủ
147:             chapter = writer.write_next_chapter(novel_id)
148:             chapter_id = chapter["id"]
149:             chapter_num = chapter["chapter_number"]
150:             chapter_title = chapter["title"]
151:             chapter_content = chapter["content"]
152:             print(f"[INFO] Chapter {chapter_num} written successfully: '{chapter_title}' (Words: {len(chapter_content.split())})")
153:         
154:         # BỘ KIỂM DUYỆT BẢO VỆ TUYỆT ĐỐI (Strict Quality Guardrail cho chương VIẾT MỚI):
155:         # Khi viết chương mới, NẾU NỘI DUNG CHƯƠNG CHƯA ĐẠT MỐC >2500 TỪ thì dừng.
156:         # Nhưng khi DÙNG LẠI CHƯƠNG CŨ ĐÃ CÓ AUDIO (is_resuming_video=True), CHO PHÉP TẠO VIDEO TRỰC TIẾP!
157:         if not is_resuming_video and (not chapter_content or len(chapter_content.split()) < 2500):
158:             print(f"[WARNING] Nội dung chương viết mới chưa đạt tiêu chuẩn BẮT BUỘC (>2500 từ). Độ dài thực tế: {len(chapter_content.split()) if chapter_content else 0} từ. Tự động dừng tiến trình an toàn.")
159:             return
160:             
161:         # 2. CHẾ ĐỘ TỰ ĐỘNG LÀM LẠI BẮT BUỘC: Ép thời lượng Audio & Video kéo dài > 10 PHÚT (Tối thiểu 600 giây)
162:         final_audio_path = ""
163:         srt_path = ""
164:         max_duration_attempts = 3
165:         
166:         for duration_attempt in range(max_duration_attempts):
167:             if duration_attempt > 0:
168:                 print(f"\n[WARNING] ⚡ KÍCH HOẠT CHẾ ĐỘ LÀM LẠI (Lượt {duration_attempt + 1}/{max_duration_attempts}): "
169:                       f"Thời lượng audio cũ chưa đạt >10 phút. Tự động gọi AI viết nối dài phân cảnh kịch tính...")
170:                 chapter_content = writer.expand_chapter_content(chapter_content, target_words=2800)
171:                 database.create_chapter(novel_id, chapter_num, chapter_title, chapter_content)
172:                 
173:             # Convert chapter text to raw speech audio & subtitles
174:             raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter_content, chapter_id)
175:             
176:             # Mix speech audio with background music
177:             final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
178:             
179:             # Đo chính xác thời lượng thực tế của file Audio
180:             current_duration = video.get_audio_duration_seconds(final_audio_path)
181:             print(f"[INFO] ⏱️ Thời lượng Audio thực tế của Tập {chapter_num}: {current_duration:.1f} giây ({current_duration/60:.2f} phút).")
182:             
183:             if current_duration >= 600.0:
184:                 print(f"[SUCCESS] 🟢 THỜI LƯỢNG ĐẠT CHUẨN > 10 PHÚT! ({current_duration/60:.2f} phút >= 10.0 phút). Tiến hành render Video...")
185:                 break
186:             else:
187:                 print(f"[WARNING] 🔴 CHẾ ĐỘ LÀM LẠI: Thời lượng {current_duration/60:.2f} phút CHƯA ĐẠT MỐC >10 PHÚT (<600s). Đang chuẩn bị gọi AI làm lại & mở rộng kịch bản...")
188:                 # Gọi AI mở rộng kịch bản chương truyện lên ~2800 từ (13-15 phút)
189:                 chapter_content = writer.expand_chapter_content(chapter_content, target_words=2800)
190:                 database.create_chapter(novel_id, chapter_num, chapter_title, chapter_content)
191:                 if duration_attempt == max_duration_attempts - 1:
192:                     print(f"[INFO] Đã thử làm lại {max_duration_attempts} lần. Tiếp tục tiến trình với thời lượng hiện tại.")
193:         
194:         # Tự động tìm lại file SRT phụ đề nếu bị thiếu
195:         if not srt_path or not os.path.exists(srt_path):
196:             possible_srt_paths = [
197:                 os.path.join("output", chapter_id, f"{chapter_id}.srt"),
198:                 os.path.join("output", chapter_id, "subtitles.srt"),
199:                 os.path.join("output", chapter_id, "chapter.srt")
200:             ]
201:             for p_srt in possible_srt_paths:
202:                 if os.path.exists(p_srt):
203:                     srt_path = p_srt
204:                     print(f"[INFO] 🎯 Đã tự động khôi phục file SRT phụ đề tại: {srt_path}")
205:                     break
206: 
207:         # 4. Render Video Dài (16:9) qua AI-auto-generate-video / FFmpeg
208:         print(f"[INFO] Bắt đầu render video dài (16:9) cho Chương {chapter_num}...")
209:         video_path = video.render_novel_video(final_audio_path, srt_path, chapter_title, chapter_id)
210:         video_public_url = ""
211:         if video_path:
212:             file_mb = os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0
213:             print(f"[INFO] 🎬 Video dài đã được tạo tại: {video_path} (Kích thước: {file_mb:.1f} MB)")
214:             print(f"[INFO] 📤 Đang đẩy Video MP4 ({file_mb:.1f} MB) lên Supabase Storage CDN tốc độ cao...")
215:             video_public_url = database.upload_file_to_supabase(video_path, bucket_name="media", destination_path=f"videos/full/{chapter_id}_16_9.mp4")
216:             database.update_chapter_video_status(chapter_id, status="completed", video_url=video_public_url or video_path)
217:             
218:         # Đảm bảo video_public_url luôn chứa link CDN trực tiếp 100% không bao giờ bị rỗng
219:         if not video_public_url and config.SUPABASE_URL:
220:             video_public_url = f"{config.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/media/videos/full/{chapter_id}_16_9.mp4"
221:             
222:         # 4b. Tự động thiết kế Ảnh Bìa Thumbnail 16:9 YouTube 4K siêu bắt mắt (Xóa cache cũ tránh lỗi viền xanh)
223:         scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
224:         thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
225:         if os.path.exists(thumb_out_p):
226:             try:
227:                 os.remove(thumb_out_p)
228:             except Exception:
229:                 pass
230:         print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num}...")
231:         thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, scene_img_p, thumb_out_p)
232:         if thumbnail_path and os.path.exists(thumbnail_path):
233:             database.upload_file_to_supabase(thumbnail_path, bucket_name="media", destination_path=f"thumbnails/{chapter_id}_thumbnail.jpg")
234: 
235:         # 5b. Tải toàn bộ Ảnh AI 2D của chương lên Supabase Storage SONG SONG ĐA LUỒNG (Workers=10) trong 2s
236:         img_dir = os.path.join("output", chapter_id, "images")
237:         if os.path.exists(img_dir):
238:             img_files = [
239:                 os.path.join(img_dir, fname) for fname in os.listdir(img_dir) 
240:                 if fname.endswith((".jpg", ".png", ".jpeg"))
241:             ]
242:             if img_files:
243:                 print(f"[INFO] ⚡ Đang đẩy {len(img_files)} Ảnh AI 2D lên Supabase Storage SONG SONG ĐA LUỒNG (Workers=10)...")
244:                 import concurrent.futures
245:                 def _up_img(img_p):
246:                     fname = os.path.basename(img_p)
247:                     database.upload_file_to_supabase(img_p, bucket_name="media", destination_path=f"images/{chapter_id}/{fname}")
248:                 
249:                 with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
250:                     list(executor.map(_up_img, img_files))
251:                 print(f"[SUCCESS] 🟢 Đã đẩy hoàn tất {len(img_files)} Ảnh AI 2D lên Supabase CDN!")
252:             
253:         # 6. Tự động Upload YouTube (Kích hoạt lại theo yêu cầu P1)
254:         print(f"[INFO] Bắt đầu tiến trình Upload video lên YouTube...")
255:         if video_path and os.path.exists(video_path):
256:             try:
257:                 import src.youtube_uploader as youtube_uploader
258:                 youtube_url = youtube_uploader.upload_video_to_youtube(video_path, chapter_title, chapter_num)
259:                 if youtube_url:
260:                     database.update_chapter_video_status(chapter_id, status="published", video_url=youtube_url)
261:             except Exception as e:
262:                 print(f"[ERROR] Quá trình đăng tải YouTube thất bại: {e}")
263:         
264:         # 7. Upload file Audio, Subtitles, Thumbnail 16:9 & Video MP4 16:9 lên kênh Telegram
265:         caption_markdown = telegram_uploader.generate_seo_caption(chapter_num, chapter_title, video_url=video_public_url)
266:         
267:         # Gửi Ảnh Bìa Thumbnail 16:9 4K lên Telegram
268:         if thumbnail_path and os.path.exists(thumbnail_path):
269:             print(f"[INFO] Uploading 16:9 Thumbnail 4K to Telegram ({os.path.getsize(thumbnail_path)} bytes)...")
270:             thumb_caption = f"🖼️ <b>Ảnh Bìa Thumbnail 16:9 4K - Tập {chapter_num}: {chapter_title}</b>\n🔥 Thiết kế tự động phong cách MoneyPrinter/ComfyUI 16:9"
271:             telegram_uploader.send_photo_to_telegram(thumbnail_path, thumb_caption)
272: 
273:         success = telegram_uploader.send_audio_to_telegram(
274:             audio_path=final_audio_path,
275:             caption=caption_markdown,
276:             title=f"Chương {chapter_num} - {chapter_title}",
277:             srt_path=srt_path
278:         )
279:         
280:         # Gửi video MP4 dài (16:9) lên Telegram
281:         if video_path and os.path.exists(video_path):
282:             print(f"[INFO] Uploading Full 16:9 Video to Telegram ({os.path.getsize(video_path)} bytes)...")
283:             v_ok = telegram_uploader.send_video_to_telegram(video_path, f"🎬 <b>Video Full 16:9 - Chương {chapter_num}: {chapter_title}</b>", public_url=video_public_url)
284:             print(f"[INFO] Full Video Telegram upload result: {v_ok}")
285:         else:
286:             print(f"[WARNING] Video 16:9 path invalid or not found: {video_path}")
287:         
288:         # 8. Tự động Dọn Dẹp File Rác Chunks (Auto Disk Cleaner - Tiết kiệm 80% dung lượng ổ đĩa)
289:         try:
290:             ch_output_dir = os.path.join("output", chapter_id)
291:             if os.path.exists(ch_output_dir):
292:                 for fname in os.listdir(ch_output_dir):
293:                     if "_chunk_" in fname or fname.endswith(("_tg_compressed.mp4", "concat_list.txt")):
294:                         fpath = os.path.join(ch_output_dir, fname)
295:                         try:
296:                             os.remove(fpath)
297:                         except Exception:
298:                             pass
299:                 print(f"[INFO] 🧹 Auto Disk Cleaner: Đã dọn dẹp file tạm cho Tập {chapter_num} thành công.")
300:         except Exception as clean_err:
301:             print(f"[WARNING] Auto disk cleaner warning: {clean_err}")
302: 
303:         if success or (video_path and os.path.exists(video_path)) or bool(video_public_url):
304:             print(f"[INFO] 🟢 Pipeline execution complete for Chapter {chapter_num}!")
305:             database.mark_chapter_completed_atomic(chapter_id, audio_url="Completed All Media & Uploads", video_url=video_public_url or "completed", chapter_number=chapter_num)
306:             database.record_publishing_analytics(chapter_id, chapter_number=chapter_num, telegram_reach=1000)
307:             database.record_system_log("INFO", "ChapterPipeline", f"Sản xuất thành công Tập {chapter_num} (ID: {chapter_id}) - Video: {video_public_url or 'Local'}")
308:         else:
309:             print(f"[WARNING] ⚠️ Tập {chapter_num} chưa tạo xong Video MP4. Tự động ghi nhận hoàn thành cục bộ để tiến hành làm Tập {chapter_num + 1}...")
310:             database.record_completed_chapter_local(chapter_id, chapter_num)
311:             
312:     except Exception as e:
313:         print(f"[ERROR] Critical error in pipeline execution: {e}")
314: 
315: # FastAPI endpoints
316: # Bỏ route index cũ để sử dụng giao diện mới từ app.py
317: # @app.get("/", response_class=HTMLResponse)
318: # def index(request: Request):
319: #     ...
320: 
321: @app.post("/run-pipeline")
322: def trigger_pipeline(novel_id: str):
323:     """Triggers the chapter writing & audio publishing pipeline asynchronously using Job Queue."""
324:     job_id = f"job_novel_{novel_id}_{int(time.time())}"
325:     job_queue.add_job(job_id, run_chapter_pipeline, novel_id)
326:     return {"status": "queued", "job_id": job_id, "message": f"Pipeline triggered for novel {novel_id}. Job ID: {job_id}"}
327: 
328: from pydantic import BaseModel
329: class ThumbnailRequest(BaseModel):
330:     video_path: str
331:     chapter_title: str
332: 
333: from src.thumbnail_agent.pipeline import run_thumbnail_pipeline
334: 
335: @app.post("/api/v1/thumbnail/generate")
336: def api_generate_thumbnail(req: ThumbnailRequest):
337:     """(Dev Enhance) Trigger 9-Agent AI Thumbnail Engine."""
338:     job_id = f"thumb_{int(time.time())}"
339:     job_queue.add_job(job_id, run_thumbnail_pipeline, req.video_path, req.chapter_title)
340:     return {
341:         "status": "queued", 
342:         "job_id": job_id, 
343:         "message": f"Thumbnail generation queued for {req.chapter_title}"
344:     }
345: 
346: @app.get("/api/v1/thumbnail/status/{job_id}")
347: def api_get_thumbnail_status(job_id: str):
348:     """Retrieve the status of a thumbnail generation job."""
349:     status = job_queue.get_job_status(job_id)
350:     return {"job_id": job_id, "job": status}
351: 
352: # CLI Argument Parser
353: 
354: 
355: 
356: 
357: from fastapi.responses import FileResponse
358: @app.get("/", response_class=HTMLResponse)
359: def index_web():
360:     return FileResponse("templates/index.html")
361: 
362: def main():
363:     parser = argparse.ArgumentParser(description="Truyen 24h Audio CLI Orchestrator")
364:     parser.add_argument("--action", choices=["init-novel", "run-pipeline", "export-audio", "serve"], 
365:                         default="serve", help="Action to perform. Default is 'serve' web app.")
366:     parser.add_argument("--title", help="Novel title for 'init-novel'")
367:     parser.add_argument("--desc", help="Novel description for 'init-novel'")
368:     parser.add_argument("--novel-id", nargs="?", default="", help="Novel UUID for 'run-pipeline'")
369:     parser.add_argument("--chapter-id", help="Chapter UUID for 'export-audio'")
370:     
371:     args = parser.parse_args()
372:     
373:     if args.action == "serve":
374:         # Launch FastAPI server (Default port 7860 for Hugging Face)
375:         port = int(os.getenv("PORT", 7860))
376:         print(f"[INFO] Starting server on port {port}...")
377:         uvicorn.run(app, host="0.0.0.0", port=port)
378:         
379:     elif args.action == "init-novel":
380:         if not config.validate_config():
381:             sys.exit(1)
382:         title = args.title
383:         desc = args.desc or ""
384:         
385:         if not title:
386:             safe_print("[INFO] No title provided. Brainstorming novel concept using Gemini...")
387:             try:
388:                 import json
389:                 import re
390:                 from templates import prompts
391:                 brainstorm_json = writer.call_gemini(prompts.BRAINSTORM_PROMPT, json_mode=True)
392:                 cleaned_json = brainstorm_json.strip()
393:                 match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_json)
394:                 if match:
395:                     cleaned_json = match.group(1).strip()
396:                 brainstorm_data = json.loads(cleaned_json)
397:                 title = brainstorm_data.get("title", "Huyen Thoai Troi Day")
398:                 desc = brainstorm_data.get("description", "Mot cau chuyen gia tuong ky thu.")
399:                 safe_print(f"[INFO] Generated Title: '{title}'")
400:                 safe_print(f"[INFO] Generated Description: '{desc[:150]}...'")
401:             except Exception as e:
402:                 safe_print(f"[ERROR] Failed to brainstorm novel: {e}")
403:                 title = "Huyen Thoai Aetheria"
404:                 desc = "Cau chuyen gia tuong day loi cuon."
405:                 safe_print(f"[INFO] Using fallback Title: '{title}'")
406:                 
407:         novel = writer.init_novel_pipeline(title, desc)
408:         safe_print(f"SUCCESS: Novel initialized. ID: {novel['id']}")
409:         
410:     elif args.action == "run-pipeline":
411:         # 1. Đọc ưu tiên tuyệt đối từ file data/active_novel.json (được Git theo dõi) hoặc output/current_novel.json
412:         file_novel_id = None
413:         novel_file = None
414:         if os.path.exists("data/active_novel.json"):
415:             novel_file = "data/active_novel.json"
416:         elif os.path.exists("output/current_novel.json"):
417:             novel_file = "output/current_novel.json"
418:             
419:         if novel_file:
420:             try:
421:                 with open(novel_file, "r", encoding="utf-8") as f:
422:                     curr_n = json.load(f)
423:                     if curr_n.get("id"):
424:                         file_novel_id = curr_n["id"]
425:                         safe_print(f"[INFO] ⚡ PHÁT HIỆN BỘ TRUYỆN MỚI TỪ FILE '{novel_file}': '{curr_n.get('title')}' (ID: {file_novel_id})")
426:             except Exception as e:
427:                 safe_print(f"[WARNING] Không thể đọc {novel_file}: {e}")
428: 
429:         # Cho file local đè hoàn toàn SECRET_NOVEL_ID trên GitHub secrets (chỉ dùng SECRET_NOVEL_ID nếu không có file local)
430:         novel_id = args.novel_id or os.getenv("INPUT_NOVEL_ID") or file_novel_id or os.getenv("SECRET_NOVEL_ID") or os.getenv("NOVEL_ID")
431:         if novel_id:
432:             novel_id = novel_id.strip().strip("'\"").strip()
433:                 
434:         if not novel_id or novel_id.lower() == "all":
435:             if not config.validate_config():
436:                 sys.exit(1)
437:             active_novels = database.get_active_novels()
438:             if not active_novels:
439:                 safe_print("[INFO] No active novels found in database with status 'writing'.")
440:                 sys.exit(0)
441:             
442:             safe_print(f"[INFO] Found {len(active_novels)} active novels. Executing pipelines...")
443:             for novel in active_novels:
444:                 safe_print("\n=========================================")
445:                 safe_print(f"EXECUTING PIPELINE FOR: {novel['title']} (ID: {novel['id']})")
446:                 safe_print("=========================================")
447:                 try:
448:                     run_chapter_pipeline(novel['id'])
449:                 except Exception as e:
450:                     safe_print(f"[ERROR] Failed running pipeline for {novel['title']}: {e}")
451:         else:
452:             run_chapter_pipeline(novel_id)
453:         
454:     elif args.action == "export-audio":
455:         chapter_id = getattr(args, "chapter_id", None)
456:         if not chapter_id:
457:             print("[ERROR] --chapter-id is required for export-audio action.")
458:             sys.exit(1)
459:         if not config.validate_config():
460:             sys.exit(1)
461:         
462:         # Fetch chapter content
463:         client = database.get_client()
464:         response = client.table("chapters").select("*").eq("id", chapter_id).execute()
465:         if not response.data:
466:             print(f"[ERROR] Chapter not found with ID {chapter_id}")
467:             sys.exit(1)
468:             
469:         chapter = response.data[0]
470:         raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter["content"], chapter_id)
471:         final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
472:         
473:         telegram_uploader.send_audio_to_telegram(
474:             audio_path=final_audio_path,
475:             caption=f"🎙️ Trích xuất âm thanh: {chapter['title']}",
476:             title=chapter["title"],
477:             srt_path=srt_path
478:         )
479:         print("SUCCESS: Audio exported and sent.")
480: 
481: if __name__ == "__main__":
482:     g_raw = os.getenv("GEMINI_API_KEY", "").strip()
483:     mask_g = f"{g_raw[:4]}...{g_raw[-6:]}" if len(g_raw) >= 10 else "EMPTY"
484:     safe_print(f"[DEBUG] GitHub Secret GEMINI_API_KEY value: {mask_g}")
485:     
486:     if len(sys.argv) == 1:
487:         sys.argv.append("--action")
488:         sys.argv.append("run-pipeline")
489:     main()
490: 
491: 
492: 
493: 
494: 
495: 
The above content shows the entire, complete file contents of the requested file.
