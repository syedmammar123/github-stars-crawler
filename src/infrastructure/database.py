from abc import ABC, abstractmethod
from typing import List
from src.domain.repository import Repository

class RepositoryDatabase(ABC):
    """
    Abstract base class for repository database operations.
    This allows us to swap between SQLite and PostgreSQL easily.
    """
    
    @abstractmethod
    async def setup(self) -> None:
        """Create tables and indexes."""
        pass
    
    @abstractmethod
    async def upsert_repositories(self, repos: List[Repository]) -> int:
        """
        Insert or update repositories.
        Returns number of rows affected.
        """
        pass
    
    @abstractmethod
    async def get_repository_count(self) -> int:
        """Get total number of repositories in database."""
        pass
    
    @abstractmethod
    async def get_all_repositories(self) -> List[Repository]:
        """Get all repositories from database."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        pass
