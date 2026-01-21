"""
Configuration Management Module
Centralized configuration for the Fund Portfolio Intelligence System
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AzureConfig(BaseModel):
    """Azure Document Intelligence Configuration"""
    endpoint: str = Field(..., description="Azure Document Intelligence endpoint")
    key: str = Field(..., description="Azure API key")
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v.startswith('https://'):
            raise ValueError('Azure endpoint must start with https://')
        return v


class GroqConfig(BaseModel):
    """Groq API Configuration"""
    api_key: str = Field(..., description="Groq API key")
    model: str = Field(
        default="moonshotai/kimi-k2-instruct-0905",
        description="Default Groq model"
    )
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class Neo4jConfig(BaseModel):
    """Neo4j Database Configuration"""
    url: str = Field(..., description="Neo4j connection URL")
    username: str = Field(default="neo4j")
    password: str = Field(..., description="Neo4j password")
    
    @validator('url')
    def validate_url(cls, v):
        if not (v.startswith('neo4j://') or v.startswith('neo4j+s://')):
            raise ValueError('Neo4j URL must start with neo4j:// or neo4j+s://')
        return v


class DatabaseConfig(BaseModel):
    """SQL Database Configuration"""
    sqlite_path: Path = Field(..., description="Path to SQLite database")
    
    @validator('sqlite_path')
    def validate_path(cls, v):
        v = Path(v)
        if not v.parent.exists():
            v.parent.mkdir(parents=True, exist_ok=True)
        return v


class DataConfig(BaseModel):
    """Data File Configuration"""
    isin_mapping_path: Path = Field(..., description="Path to ISIN master data")
    raw_data_dir: Path = Field(default=Path("data/raw"))
    processed_data_dir: Path = Field(default=Path("data/processed"))
    
    @validator('isin_mapping_path', 'raw_data_dir', 'processed_data_dir')
    def validate_data_path(cls, v):
        v = Path(v)
        if not v.exists() and 'dir' in v.name:
            v.mkdir(parents=True, exist_ok=True)
        return v


class Settings(BaseSettings):
    """Main Application Settings"""
    
    # Project Info
    project_name: str = "Fund Portfolio Intelligence System"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Azure Configuration
    azure_endpoint: str = Field(..., env="AZURE_ENDPOINT")
    azure_key: str = Field(..., env="AZURE_KEY")
    
    # Groq Configuration
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_model: str = Field(
        default="moonshotai/kimi-k2-instruct-0905",
        env="GROQ_MODEL"
    )
    groq_temperature: float = Field(default=0.1, env="GROQ_TEMPERATURE")
    
    # Neo4j Configuration
    neo4j_url: str = Field(..., env="NEO4J_URL")
    neo4j_username: str = Field(default="neo4j", env="NEO4J_USERNAME")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    
    # Database Configuration
    sqlite_db_path: str = Field(..., env="SQLITE_DB_PATH")
    
    # Data Paths
    isin_mapping_path: str = Field(..., env="ISIN_MAPPING_PATH")
    raw_data_dir: str = Field(default="data/raw", env="RAW_DATA_DIR")
    processed_data_dir: str = Field(default="data/processed", env="PROCESSED_DATA_DIR")
    
    # Processing Configuration
    max_parallel_pdf: int = Field(default=3, env="MAX_PARALLEL_PDF")
    batch_size: int = Field(default=10, env="BATCH_SIZE")
    
    # Query Configuration
    sql_query_timeout: int = Field(default=30, env="SQL_QUERY_TIMEOUT")
    graph_query_timeout: int = Field(default=30, env="GRAPH_QUERY_TIMEOUT")
    top_k_results: int = Field(default=10, env="TOP_K_RESULTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def azure(self) -> AzureConfig:
        """Get Azure configuration"""
        return AzureConfig(
            endpoint=self.azure_endpoint,
            key=self.azure_key
        )
    
    @property
    def groq(self) -> GroqConfig:
        """Get Groq configuration"""
        return GroqConfig(
            api_key=self.groq_api_key,
            model=self.groq_model,
            temperature=self.groq_temperature
        )
    
    @property
    def neo4j(self) -> Neo4jConfig:
        """Get Neo4j configuration"""
        return Neo4jConfig(
            url=self.neo4j_url,
            username=self.neo4j_username,
            password=self.neo4j_password
        )
    
    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            sqlite_path=Path(self.sqlite_db_path)
        )
    
    @property
    def data(self) -> DataConfig:
        """Get data configuration"""
        return DataConfig(
            isin_mapping_path=Path(self.isin_mapping_path),
            raw_data_dir=Path(self.raw_data_dir),
            processed_data_dir=Path(self.processed_data_dir)
        )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Export commonly used configs
def get_azure_config() -> AzureConfig:
    """Get Azure configuration"""
    return get_settings().azure


def get_groq_config() -> GroqConfig:
    """Get Groq configuration"""
    return get_settings().groq


def get_neo4j_config() -> Neo4jConfig:
    """Get Neo4j configuration"""
    return get_settings().neo4j


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_settings().database


def get_data_config() -> DataConfig:
    """Get data configuration"""
    return get_settings().data


if __name__ == "__main__":
    # Test configuration loading
    settings = get_settings()
    print(f"Project: {settings.project_name} v{settings.version}")
    print(f"Azure Endpoint: {settings.azure.endpoint}")
    print(f"Neo4j URL: {settings.neo4j.url}")
    print(f"Database Path: {settings.database.sqlite_path}")
