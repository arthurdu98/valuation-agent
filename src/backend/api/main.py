"""FastAPI application entry point.

Run with:
    uvicorn src.api.main:app --reload --port 8000

⚠ MUST use a single worker (default). The run_registry and CompanyManager hold
process-local state; multiple workers would silently partition them.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.config import CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: pre-warm shared objects on startup."""
    # Import lazily to avoid paying module-load cost at import time in tests.
    from src.backend.api.deps import get_company_manager

    get_company_manager()  # warm the class-level dict
    yield


app = FastAPI(
    title="估值监控 API",
    description="多行业估值监控与智能体辩证分析系统 — REST API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
from src.backend.api.routers.companies import router as companies_router  # noqa: E402
from src.backend.api.routers.industries import router as industries_router, compare_router  # noqa: E402
from src.backend.api.routers.runs import router as runs_router  # noqa: E402
from src.backend.api.routers.metrics import router as metrics_router  # noqa: E402
from src.backend.api.routers.reports import router as reports_router  # noqa: E402

app.include_router(companies_router)
app.include_router(industries_router)
app.include_router(compare_router)
app.include_router(runs_router)
app.include_router(metrics_router)
app.include_router(reports_router)


# --- Health check ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "valuation-api"}
