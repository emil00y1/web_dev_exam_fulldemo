from dotenv import load_dotenv
import os
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()

# Environment setting
ENVIRONMENT = os.getenv('FLASK_ENV', 'development')

class BaseConfig:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'development-key')
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Email settings
    EMAIL_SENDER = os.getenv('EMAIL_SENDER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    
    # Role IDs remain the same...

class DevelopmentConfig(BaseConfig):
    # Use Docker environment variables
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'mysql'),  # From docker-compose environment
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'password'),
        'database': os.getenv('DB_NAME', 'company')
    }
    SESSION_FILE_DIR = '/tmp/flask_session'
    UPLOAD_FOLDER = './images'
    AVATAR_FOLDER = './static/avatars'
    DEBUG = True

class ProductionConfig(BaseConfig):
    # Use production environment variables
    DB_CONFIG = {
        'host': os.getenv('PROD_DB_HOST'),
        'user': os.getenv('PROD_DB_USER'),
        'password': os.getenv('PROD_DB_PASSWORD'),
        'database': os.getenv('PROD_DB_NAME')
    }
    SESSION_FILE_DIR = '/home/emil00y1/web_dev_exam_fulldemo/flask_session'
    UPLOAD_FOLDER = '/home/emil00y1/web_dev_exam_fulldemo/images'
    AVATAR_FOLDER = '/home/emil00y1/web_dev_exam_fulldemo/static/avatars'
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

def get_config():
    return ProductionConfig if ENVIRONMENT == 'production' else DevelopmentConfig

config = get_config()