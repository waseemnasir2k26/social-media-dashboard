from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.models import init_db
from app.routers import posts_router, platforms_router
from app.services import get_scheduler_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    scheduler = get_scheduler_service()
    scheduler.start()
    print(" Social Media Dashboard API started")
    print(f" API docs available at /docs")

    yield

    # Shutdown
    scheduler.stop()
    print(" Social Media Dashboard API stopped")


app = FastAPI(
    title="Social Media Dashboard API",
    description="API for managing and scheduling social media posts across multiple platforms",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(posts_router, prefix="/api")
app.include_router(platforms_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Social Media Dashboard API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
