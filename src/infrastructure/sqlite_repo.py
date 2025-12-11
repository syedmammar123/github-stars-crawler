import aiosqlite
from typing import List
from datetime import datetime, timezone
from src.infrastructure.database import RepositoryDatabase
from src.domain.repository import Repository

class SQLiteRepository(RepositoryDatabase):
    """SQLite implementation of repository database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    async def _get_connection(self):
        """Get or create database connection."""
        if self.connection is None:
            self.connection = await aiosqlite.connect(self.db_path)
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection
    
    async def setup(self) -> None:
        """Create tables and indexes."""
        conn = await self._get_connection()
        
        # Create repositories table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL UNIQUE,
                star_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_crawled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_full_name 
            ON repositories(full_name)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_star_count 
            ON repositories(star_count DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_last_crawled 
            ON repositories(last_crawled_at)
        """)
        
        await conn.commit()
        print("✅ SQLite database setup complete")
    
    async def upsert_repositories(self, repos: List[Repository]) -> int:
        """
        Insert or update repositories using UPSERT.
        Returns number of rows affected.
        """
        if not repos:
            return 0
        
        conn = await self._get_connection()
        rows_affected = 0
        
        for repo in repos:
            cursor = await conn.execute("""
                INSERT INTO repositories (
                    id, full_name, star_count, last_crawled_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    star_count = excluded.star_count,
                    last_crawled_at = excluded.last_crawled_at,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                repo.id,
                repo.full_name,
                repo.star_count,
                repo.last_crawled_at.isoformat() if repo.last_crawled_at else datetime.now(timezone.utc).isoformat()
            ))
            rows_affected += cursor.rowcount
        
        await conn.commit()
        return rows_affected
    
    async def get_repository_count(self) -> int:
        """Get total number of repositories in database."""
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT COUNT(*) FROM repositories")
        result = await cursor.fetchone()
        return result[0] if result else 0
    
    async def get_all_repositories(self) -> List[Repository]:
        """Get all repositories from database."""
        conn = await self._get_connection()
        cursor = await conn.execute("""
            SELECT id, full_name, star_count, created_at, updated_at, last_crawled_at
            FROM repositories
            ORDER BY star_count DESC
        """)
        
        rows = await cursor.fetchall()
        repositories = []
        
        for row in rows:
            repo = Repository(
                id=row[0],
                full_name=row[1],
                star_count=row[2],
                created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                updated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                last_crawled_at=datetime.fromisoformat(row[5]) if row[5] else None
            )
            repositories.append(repo)
        
        return repositories
    
    async def close(self) -> None:
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None