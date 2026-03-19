"""
MCServerPanel - Main Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from backend.config import settings
from backend.database import init_db
from backend.routes import auth, servers, modpacks, mods, plugins, system
from backend.routes.auth import VALID_TOKENS

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Include routers
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(modpacks.router)
app.include_router(mods.router)
app.include_router(plugins.router)
app.include_router(system.router)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    allowed_paths = {
        "/api/auth/login",
        "/api/docs",
        "/api/redoc",
        "/openapi.json",
        "/health",
        "/",
    }

    if path.startswith("/api") and path not in allowed_paths:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "", 1).strip() if auth_header.startswith("Bearer ") else ""
        if token not in VALID_TOKENS:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION} — API running at /api/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
