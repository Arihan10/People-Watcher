from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import characters, relationships, interaction_sessions, context

app = FastAPI(
    title="AI Life Simulation API",
    description="Backend API for AI-powered life simulation with characters, relationships, and spaces",
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
app.include_router(relationships.router)
app.include_router(interaction_sessions.router)
app.include_router(context.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "AI Life Simulation API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

