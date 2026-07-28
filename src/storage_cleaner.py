import os
import shutil

def cleanup_temporary_artifacts(chapter_id: str, keep_video: bool = True):
    """Feature 9: Quản lý dọn dẹp các tệp ảnh/audio tạm sau khi render video thành công để tiết kiệm dung lượng đĩa đệm."""
    target_dir = os.path.join("output", chapter_id)
    if not os.path.exists(target_dir):
        return
        
    scenes_dir = os.path.join(target_dir, "scenes")
    if os.path.exists(scenes_dir):
        try:
            shutil.rmtree(scenes_dir)
            print(f"[CLEANUP] Cleaned temporary scene images directory: {scenes_dir}")
        except Exception as e:
            print(f"[WARNING] Could not cleanup scenes dir: {e}")
            
    concat_list = os.path.join(target_dir, "concat_list.txt")
    if os.path.exists(concat_list):
        try:
            os.remove(concat_list)
        except Exception:
            pass
