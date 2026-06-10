"""FastAPI entrypoint for the Provider Contract Change Validation Engine.

A thin API layer over the deterministic decision core. The reference workbook is
loaded ONCE in the lifespan handler; routers read it through ``get_store``.

Run with:  uvicorn api.main:app --reload
"""

from __future__ import annotations

import os
import pathlib
import sys
from contextlib import asynccontextmanager

# Make the project root importable so `import engine` works under `uvicorn` and pytest.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.deps import load_store  # noqa: E402
from api.routers import decisions, health, reference  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the workbook exactly once and stash it on app state."""
    app.state.store = load_store()
    yield


def _allowed_origins() -> list[str]:
    """Parse ``ALLOWED_ORIGINS`` (comma-separated). Default: none."""
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _configure_cors(application: FastAPI) -> None:
    """Enable CORS when ``ALLOWED_ORIGINS`` is set (comma-separated, or ``*``)."""
    origins = _allowed_origins()
    if not origins:
        return
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if origins == ["*"] else origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


app = FastAPI(
    title="Provider Contract Change Validation API",
    description=(
        "Thin REST layer over the deterministic CMS-855I decision engine. "
        "Business outcomes return 200; 4xx is reserved for transport errors."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

_configure_cors(app)

app.include_router(health.router)
app.include_router(decisions.router)
app.include_router(reference.router)
