import os
from pymongo import MongoClient
from shared.config.config import get_config
from pymongo.errors import ConnectionFailure

class MongoDB:
    def __init__(self):
        try:
            config = get_config(os.environ.get('FLASK_ENV', 'development'))
            # Create a MongoDB client
            self.db_client = MongoClient(config.MONGO_URI)
            
            # Test connection
            self.db_client.admin.command('ping')
            print("✅ Connected to MongoDB successfully")
        except ConnectionFailure:
            print("❌ Failed to connect to MongoDB.")

mongo_db = MongoDB()
