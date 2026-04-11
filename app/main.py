import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.init import auto_register_routers
from app.middleware import common as middleware_main


FRONTEND_DIST_DIR = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"


def setup_frontend(app: FastAPI) -> None:
    if not FRONTEND_INDEX_FILE.exists():
        return

    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    favicon_file = FRONTEND_DIST_DIR / "favicon.svg"
    if favicon_file.exists():

        @app.get("/favicon.svg", include_in_schema=False)
        def frontend_favicon() -> FileResponse:
            return FileResponse(favicon_file)

    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_INDEX_FILE)

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(FRONTEND_INDEX_FILE)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.state.settings = settings

    middleware_main.setup_cors(app)
    middleware_main.setup_process_time_middleware(app)
    middleware_main.setup_http_exception_handler(app)
    middleware_main.setup_logging_middleware(app)
    middleware_main.setup_audit_middleware(app)

    api_pkg = "app.api"
    api_path = pathlib.Path(__file__).parent / "api"
    auto_register_routers(app, api_pkg, api_path)
    setup_frontend(app)
    return app


app = create_app()
