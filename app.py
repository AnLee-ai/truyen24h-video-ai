import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from src.main import app as fastapi_app

# 1. Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)
fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 2. CORS setup
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, set to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Setup templates and static files
templates = Jinja2Templates(directory="templates")
fastapi_app.mount("/static", StaticFiles(directory="templates"), name="static")

# 4. Include Routers
from src.api.routers import settings, pipelines, tts, novels
fastapi_app.include_router(settings.router, prefix="/api", tags=["Settings"])
fastapi_app.include_router(pipelines.router, prefix="/api", tags=["Pipelines"])
fastapi_app.include_router(tts.router, prefix="/api", tags=["TTS"])
fastapi_app.include_router(novels.router, prefix="/api", tags=["Novels"])

@fastapi_app.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@fastapi_app.get("/health")
@limiter.limit("120/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "ok", "service": "Truyen24h Audio Engine"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("app:fastapi_app", host="0.0.0.0", port=port)
