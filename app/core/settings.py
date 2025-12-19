"""Application settings."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


# Unified DB path - relative to repo root, resolved absolutely
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "duckdb" / "cps_growth.duckdb"


class Settings(BaseSettings):
    """Application settings."""
    
    # Database - use unified DB_PATH
    duckdb_path: Path = DB_PATH
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8081"))
    
    # HuggingFace
    hf_token: str = os.getenv("HF_TOKEN", "")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Paths
    project_root: Path = PROJECT_ROOT
    config_dir: Path = PROJECT_ROOT / "configs"
    data_dir: Path = PROJECT_ROOT / "data"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "duckdb").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "raw").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "raw" / "tianchi").mkdir(parents=True, exist_ok=True)

