import os
from dataclasses import dataclass
from enum import Enum

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"

@dataclass(frozen=True)
class Config:
    """Application configuration."""
    
    # GitHub API
    github_token: str
    github_api_url: str = "https://api.github.com/graphql"
    
    # Database type
    db_type: DatabaseType = DatabaseType.SQLITE
    
    # PostgreSQL settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "github_crawler"
    db_user: str = "postgres"
    db_password: str = "postgres"
    
    # SQLite settings
    sqlite_path: str = "github_crawler.db"
    
    # Crawler settings
    repos_to_crawl: int = 100_000
    batch_size: int = 100  # GraphQL max per request
    max_concurrent_requests: int = 5
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        # Determine database type from environment
        db_type_str = os.getenv('DB_TYPE', 'sqlite').lower()
        db_type = DatabaseType.POSTGRES if db_type_str == 'postgres' else DatabaseType.SQLITE
        
        return cls(
            github_token=os.getenv('GITHUB_TOKEN', ''),
            db_type=db_type,
            db_host=os.getenv('DB_HOST', 'localhost'),
            db_port=int(os.getenv('DB_PORT', '5432')),
            db_name=os.getenv('DB_NAME', 'github_crawler'),
            db_user=os.getenv('DB_USER', 'postgres'),
            db_password=os.getenv('DB_PASSWORD', 'postgres'),
            sqlite_path=os.getenv('SQLITE_PATH', 'github_crawler.db'),
            repos_to_crawl=int(os.getenv('REPOS_TO_CRAWL', '100000')),
        )
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"