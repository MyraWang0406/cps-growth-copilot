"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import health, metrics, diagnosis, opportunities, alerts

app = FastAPI(
    title="CPS Growth Copilot API",
    description="API for CPS Growth Copilot",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(diagnosis.router)
app.include_router(opportunities.router)
app.include_router(alerts.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CPS Growth Copilot API",
        "version": "1.0.0",
        "docs": "/docs",
    }

