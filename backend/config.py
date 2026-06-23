import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    # MongoDB Atlas Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://username:password@cluster.mongodb.net/luminalife?retryWrites=true&w=majority')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'lumina_life')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # JWT Configuration
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-key')
    JWT_EXPIRATION_HOURS = 24
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
    
    # API Configuration
    API_PREFIX = '/api'