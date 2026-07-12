from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.errors import InvalidPullRequestUrlError
from app.models.errors import ApiError, ApiErrorResponse


def invalid_pull_request_url_exception_handler(
    _request: Request,
    exception: InvalidPullRequestUrlError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiErrorResponse(
            error=ApiError(code=exception.code, message=exception.message)
        ).model_dump(),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.add_exception_handler(
        InvalidPullRequestUrlError,
        invalid_pull_request_url_exception_handler,
    )
    app.include_router(health_router)
    app.include_router(api_v1_router)
    return app


app = create_app()
