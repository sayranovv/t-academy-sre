import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.reload,
        reload_dirs=["app"] if settings.reload else None,
        log_level=settings.log_level,
        access_log=False,
        timeout_graceful_shutdown=settings.shutdown_timeout,
    )
