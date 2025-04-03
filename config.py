import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    """Base configuration"""
    # App settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", 3000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # OpenAI API settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_IMAGE_MODEL = "dall-e-3"
    
    # Usage limits
    MAX_REQUESTS_PER_DAY = int(os.getenv("MAX_REQUESTS_PER_DAY", 100))
    MAX_TOKENS_PER_DAY = int(os.getenv("MAX_TOKENS_PER_DAY", 100000))
    MAX_IMAGES_PER_DAY = int(os.getenv("MAX_IMAGES_PER_DAY", 50))
    
    # Feature flags
    ENABLE_CACHING = os.getenv("ENABLE_CACHING", "True").lower() == "true"
    ENABLE_IMAGE_GENERATION = os.getenv("ENABLE_IMAGE_GENERATION", "True").lower() == "true"
    ENABLE_USAGE_TRACKING = os.getenv("ENABLE_USAGE_TRACKING", "True").lower() == "true"
    
    # Cache settings
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", 3600))  # 1 hour
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # CORS settings
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # In production, force secure settings
    def __init__(self):
        if self.SECRET_KEY == "dev":
            raise ValueError("Production mode requires a secure SECRET_KEY")
        
        # Override CORS in production to be more restrictive if not explicitly set
        if "*" in self.CORS_ALLOWED_ORIGINS and not os.getenv("CORS_ALLOWED_ORIGINS"):
            self.CORS_ALLOWED_ORIGINS = ["https://yoursite.com"]

# Choose configuration based on environment
ENV = os.getenv("FLASK_ENV", "development")
if ENV == "production":
    AppConfig = ProductionConfig
else:
    AppConfig = DevelopmentConfig 