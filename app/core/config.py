from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Estimation Bot API"
    VERSION: str = "1.0.0"
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"  # Using latest available model
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2000
    
    # Qdrant Configuration
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "Enatega-Estimator"
    
    # Estimation Configuration
    DEFAULT_HOURLY_RATE: float = 30.0  # Company uses $30/hour
    BUFFER_PERCENTAGE: float = 0.20  # 20% buffer
    
    # File Paths
    DATA_DIR: str = "."
    PDF_FILES: list = [
        "Estimation Calculator Data.pdf",
        "content (3).pdf",
        "content (4).pdf",
        "content (5).pdf",
        "content (6).pdf",
        "content (7).pdf",
        "content (8).pdf"
    ]
    DOCX_FILES: list = [
        "Enatega_Product_Overview.docx"
    ]
    
    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
