import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, conversations, messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MedAI Backend",
    version="1.0.0",
    description="Bilingual Medical Education AI Assistant API — Tamil & English",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
origins = (
    ["*"]
    if settings.allowed_origins.strip() == "*"
    else [o.strip() for o in settings.allowed_origins.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate limiting (applied before routers are executed)
# ---------------------------------------------------------------------------
app.add_middleware(
    RateLimitMiddleware,
    max_per_minute=settings.max_requests_per_minute,
    max_per_day=settings.max_requests_per_day,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(messages.router, prefix="/api/v1", tags=["messages"])


# ---------------------------------------------------------------------------
# Root and Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def root():
    """Welcome endpoint with service information and link to documentation."""
    return {
        "service": "MedAI Backend",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health", tags=["health"])
async def health():
    """Simple liveness probe used by Render and load balancers."""
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log type only — never log request bodies or tokens
    logger.error(
        f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )
