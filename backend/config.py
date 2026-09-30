import os
from dotenv import load_dotenv

# Load environment variables from .env file with override=True
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path=env_path, override=True)

class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'library_db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'library-system-secure-session-key-2026')
    FLASK_PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
