import requests
import json
import sys

# Đảm bảo in UTF-8 không bị lỗi cp1252 trên Windows PowerShell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = "AnLee-ai/truyen24h-video-ai"

def get_latest_action_status():
    """Kiểm tra trực tiếp tiến trình GitHub Actions đang chạy."""
    url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=3"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"[ERROR] Cannot fetch GitHub Actions: {r.status_code}")
        return
        
    runs = r.json().get("workflow_runs", [])
    if not runs:
        print("[INFO] No workflow runs found.")
        return
        
    print(f"\n=======================================================")
    print(f" GITHUB ACTIONS LIVE MONITORING TOOL")
    print(f"=======================================================\n")
    
    for run in runs:
        run_id = run["id"]
        status = run["status"]
        conclusion = run["conclusion"] or "Đang chạy..."
        created_at = run["created_at"]
        name = run["name"]
        
        print(f"[RUN ID: {run_id}]")
        print(f"   * Workflow: {name}")
        print(f"   * Status: {status.upper()} ({conclusion})")
        print(f"   * Created: {created_at}")
        
        # Chi tiết các bước (Steps)
        jobs_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs"
        rj = requests.get(jobs_url)
        if rj.status_code == 200:
            jobs = rj.json().get("jobs", [])
            for j in jobs:
                print(f"   [JOB] {j['name']} ({j['status'].upper()})")
                for s in j.get("steps", []):
                    s_icon = "[OK]" if s["status"] == "completed" else ("--->" if s["status"] == "in_progress" else "[..]")
                    print(f"      {s_icon} [{s['status'].upper()}] {s['name']}")
        print("-" * 55)

if __name__ == "__main__":
    get_latest_action_status()
