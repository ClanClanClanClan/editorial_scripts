"""
Configuration management for Editorial Scripts
Uses environment variables and .env files
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="editorial_scripts", env="DB_NAME")
    user: str = Field(default="editorial", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    
    # Connection pool settings
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    @property
    def async_url(self) -> str:
        """Get async database URL for SQLAlchemy"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def sync_url(self) -> str:
        """Get sync database URL for migrations"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    class Config:
        env_prefix = "DB_"


class RedisSettings(BaseSettings):
    """Redis cache configuration"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    
    # Cache settings
    default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")
    max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    @property
    def url(self) -> str:
        """Get Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_prefix = "REDIS_"


class BrowserSettings(BaseSettings):
    """Browser automation settings"""
    headless: bool = Field(default=True, env="BROWSER_HEADLESS")
    timeout: int = Field(default=30000, env="BROWSER_TIMEOUT")  # milliseconds
    viewport_width: int = Field(default=1920, env="BROWSER_WIDTH")
    viewport_height: int = Field(default=1080, env="BROWSER_HEIGHT")
    
    # Pool settings
    pool_size: int = Field(default=3, env="BROWSER_POOL_SIZE")
    max_pages_per_browser: int = Field(default=5, env="BROWSER_MAX_PAGES")
    
    # Stealth settings
    use_stealth: bool = Field(default=True, env="BROWSER_USE_STEALTH")
    user_agent: Optional[str] = Field(default=None, env="BROWSER_USER_AGENT")
    
    class Config:
        env_prefix = "BROWSER_"


class AISettings(BaseSettings):
    """AI service configuration"""
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    
    # Request settings
    max_tokens: int = Field(default=4000, env="AI_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="AI_TEMPERATURE")
    request_timeout: int = Field(default=60, env="AI_REQUEST_TIMEOUT")
    
    # Retry settings
    max_retries: int = Field(default=3, env="AI_MAX_RETRIES")
    retry_delay: int = Field(default=1, env="AI_RETRY_DELAY")
    
    class Config:
        env_prefix = "AI_"


class JournalCredentials(BaseSettings):
    """Journal login credentials"""
    # SIAM journals (SICON, SIFIN)
    orcid_email: Optional[str] = Field(default=None, env="ORCID_EMAIL")
    orcid_password: Optional[str] = Field(default=None, env="ORCID_PASSWORD")
    
    # ScholarOne journals (MF, MOR)
    scholarone_email: Optional[str] = Field(default=None, env="SCHOLARONE_EMAIL")
    scholarone_password: Optional[str] = Field(default=None, env="SCHOLARONE_PASSWORD")
    
    # Gmail for 2FA
    gmail_credentials_path: Optional[str] = Field(default="credentials.json", env="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: Optional[str] = Field(default="token.json", env="GMAIL_TOKEN_PATH")
    
    @validator("gmail_credentials_path", "gmail_token_path")
    def validate_paths(cls, v):
        if v and not Path(v).exists():
            # Create parent directory if it doesn't exist
            Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v


class Settings(BaseSettings):
    """Main application settings"""
    # Application
    app_name: str = Field(default="Editorial Scripts", env="APP_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Security
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    cors_origins: list = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # File storage
    data_dir: Path = Field(default=Path("data"), env="DATA_DIR")
    pdf_dir: Path = Field(default=Path("data/pdfs"), env="PDF_DIR")
    export_dir: Path = Field(default=Path("data/exports"), env="EXPORT_DIR")
    
    # Database settings directly included
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="editorial_scripts", env="DB_NAME")
    db_user: str = Field(default="editorial", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    
    # AI settings
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Browser settings
    browser_headless: bool = Field(default=True, env="BROWSER_HEADLESS")
    browser_timeout: int = Field(default=30000, env="BROWSER_TIMEOUT")
    browser_viewport_width: int = Field(default=1920, env="BROWSER_WIDTH")
    browser_viewport_height: int = Field(default=1080, env="BROWSER_HEIGHT")
    browser_pool_size: int = Field(default=3, env="BROWSER_POOL_SIZE")
    browser_use_stealth: bool = Field(default=True, env="BROWSER_USE_STEALTH")
    browser_user_agent: Optional[str] = Field(default=None, env="BROWSER_USER_AGENT")
    
    # Credentials
    orcid_email: Optional[str] = Field(default=None, env="ORCID_EMAIL")
    orcid_password: Optional[str] = Field(default=None, env="ORCID_PASSWORD")
    
    # MF Journal credentials
    mf_username: Optional[str] = Field(default=None, env="MF_USER")
    mf_password: Optional[str] = Field(default=None, env="MF_PASS")
    
    # MOR Journal credentials
    mor_username: Optional[str] = Field(default=None, env="MOR_USER")
    mor_password: Optional[str] = Field(default=None, env="MOR_PASS")
    
    # ScholarOne platform credentials (fallback for MF, MOR)
    scholarone_username: Optional[str] = Field(default=None, env="SCHOLARONE_USER")
    scholarone_password: Optional[str] = Field(default=None, env="SCHOLARONE_PASS")
    
    # Gmail credentials for email-based scrapers (JOTA, FS)
    gmail_credentials_path: Optional[str] = Field(default="credentials.json", env="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: Optional[str] = Field(default="token.json", env="GMAIL_TOKEN_PATH")
    
    # MAFE Journal credentials
    mafe_username: Optional[str] = Field(default=None, env="MAFE_USER")
    mafe_password: Optional[str] = Field(default=None, env="MAFE_PASS")
    
    # NACO Journal credentials
    naco_username: Optional[str] = Field(default=None, env="NACO_USER")
    naco_password: Optional[str] = Field(default=None, env="NACO_PASS")
    
    @property
    def database_url(self) -> str:
        """Get async database URL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @validator("data_dir", "pdf_dir", "export_dir")
    def create_directories(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience exports (remove global instantiation)