from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import connect_to_mongo, close_mongo_connection
from .routes import characters, context, interactions, generation, reset

app = FastAPI(
    title="AI Village Simulation API",
    description="Backend API for AI-powered village simulation with characters, relationships, and interactions",
    version="1.0.0"
)

# CORS middleware for Unity integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB on startup."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown."""
    await close_mongo_connection()


# Include routers
app.include_router(characters.router)
app.include_router(context.router)
app.include_router(interactions.router)
app.include_router(generation.router)
app.include_router(reset.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "AI Village Simulation API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

