from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, leads
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, request_context_middleware


# App factory: tests can build an app with overridden settings without touching globals.
def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    # Registered before CORS so CORS is the outermost layer: preflight requests are answered
    # directly, and error responses (including 500s) still get CORS headers the browser needs.
    app.middleware("http")(request_context_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        # Lets the browser app read the request id, e.g. to show it in an error message.
        expose_headers=[REQUEST_ID_HEADER],
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(leads.router)
    return app


app = create_app()
