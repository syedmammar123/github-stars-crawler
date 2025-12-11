from src.config import Config, DatabaseType
from src.infrastructure.database import RepositoryDatabase
from src.infrastructure.sqlite_repo import SQLiteRepository
from src.infrastructure.postgres_repo import PostgreSQLRepository

def create_database(config: Config) -> RepositoryDatabase:
    """
    Factory function to create appropriate database instance.
    This is our dependency injection pattern!
    """
    if config.db_type == DatabaseType.SQLITE:
        print(f"🗄️  Using SQLite database: {config.sqlite_path}")
        return SQLiteRepository(config.sqlite_path)
    else:
        print(f"🗄️  Using PostgreSQL database: {config.postgres_url}")
        return PostgreSQLRepository(config.postgres_url)