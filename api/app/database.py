from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


class Database:
    """MongoDB database connection manager."""
    
    client: AsyncIOMotorClient = None
    
    
db = Database()


async def connect_to_mongo():
    """Connect to MongoDB on application startup."""
    db.client = AsyncIOMotorClient(settings.mongo_db_uri)
    print(f"Connected to MongoDB at {settings.mongo_db_uri}")


async def close_mongo_connection():
    """Close MongoDB connection on application shutdown."""
    db.client.close()
    print("Closed MongoDB connection")


def get_database():
    """Get the database instance."""
    return db.client[settings.database_name]

