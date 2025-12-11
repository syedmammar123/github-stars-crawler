import psycopg2
from psycopg2.extras import execute_values
from typing import List
from datetime import datetime
from src.infrastructure.database import RepositoryDatabase
from src.domain.repository import Repository

class PostgreSQLRepository(RepositoryDatabase):
    """PostgreSQL implementation of repository database."""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection = None
    
    def _get_connection(self):
        """Get or create database connection."""
        if self.connection is None or self.connection.closed:
            self.connection = psycopg2.connect(self.connection_url)
        return self.connection
    
    async def setup(self) -> None:
        """Create tables and indexes."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Read and execute the setup SQL file
        # For now, we'll inline it, but you can read from setup_database.sql
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id BIGINT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL UNIQUE,
                star_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_crawled_at TIMESTAMP NOT NULL DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'::jsonb
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_full_name 
            ON repositories(full_name);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_star_count 
            ON repositories(star_count DESC);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_last_crawled 
            ON repositories(last_crawled_at);
        """)
        
        conn.commit()
        cursor.close()
        print("✅ PostgreSQL database setup complete")
    
    async def upsert_repositories(self, repos: List[Repository]) -> int:
        """
        Insert or update repositories using UPSERT.
        Returns number of rows affected.
        """
        if not repos:
            return 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Prepare data for batch insert
        values = [
            (
                repo.id,
                repo.full_name,
                repo.star_count,
                repo.last_crawled_at or datetime.now()
            )
            for repo in repos
        ]
        
        # Batch UPSERT using execute_values (much faster!)
        execute_values(
            cursor,
            """
            INSERT INTO repositories (id, full_name, star_count, last_crawled_at)
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                star_count = EXCLUDED.star_count,
                last_crawled_at = EXCLUDED.last_crawled_at,
                updated_at = NOW()
            """,
            values
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        cursor.close()
        
        return rows_affected
    
    async def get_repository_count(self) -> int:
        """Get total number of repositories in database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM repositories")
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0
    
    async def get_all_repositories(self) -> List[Repository]:
        """Get all repositories from database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, full_name, star_count, created_at, updated_at, last_crawled_at
            FROM repositories
            ORDER BY star_count DESC
        """)
        
        rows = cursor.fetchall()
        repositories = []
        
        for row in rows:
            repo = Repository(
                id=row[0],
                full_name=row[1],
                star_count=row[2],
                created_at=row[3],
                updated_at=row[4],
                last_crawled_at=row[5]
            )
            repositories.append(repo)
        
        cursor.close()
        return repositories
    
    async def close(self) -> None:
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None