"""
FastAPI Main Application.
Configures middleware, routes, database initialization, and static UI mounting.
"""

import os
import sys

# Ensure project root directory is in sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import logger
from app.models.database import init_db
from app.api.routes_agent import router as agent_router
from app.api.routes_orders import router as orders_router
from app.api.routes_tickets import router as tickets_router
from app.api.routes_health import router as health_router
from data.seed_data import seed_database
from app.rag.retriever import retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    # Initialize DB & Seed initial data if empty
    init_db()
    seed_database()
    # Initialize RAG vector store
    retriever._initialize_store()
    logger.info("Application startup completed.")
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-oriented AI Restaurant Support & Operations Agent with Tool Calling, RAG, and Workflow Automation.",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(agent_router)
app.include_router(orders_router)
app.include_router(tickets_router)
app.include_router(health_router)

# Mount Static UI Files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
static_dir = os.path.join(frontend_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve main web chat UI."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.APP_NAME}. Please visit /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
