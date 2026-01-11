from motor.motor_asyncio import AsyncIOMotorClient
from .config import get_settings
import logging

logger = logging.getLogger(__name__)

# Global database client
mongodb_client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB on application startup."""
    global mongodb_client, database
    
    settings = get_settings()
    
    try:
        mongodb_client = AsyncIOMotorClient(settings.mongo_uri)
        database = mongodb_client.village_sim  # Explicitly use village_sim database
        
        # Test connection
        await database.command("ping")
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes for better performance
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection on application shutdown."""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("Closed MongoDB connection")


async def create_indexes():
    """Create database indexes for better query performance."""
    global database
    
    # Characters indexes
    await database.characters.create_index("is_in_interaction")
    await database.characters.create_index("last_known_space")
    
    # Relationships indexes
    await database.relationships.create_index("characters")
    await database.relationships.create_index("is_interacting")
    
    # Interaction sessions indexes
    await database.interaction_sessions.create_index("participants")
    await database.interaction_sessions.create_index("is_active")
    
    # Spaces indexes
    await database.spaces.create_index("characters_present")
    
    logger.info("Database indexes created")


def get_database():
    """Get the database instance."""
    return database
