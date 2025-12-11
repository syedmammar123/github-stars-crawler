"""
Crawler Service - Orchestrates the GitHub repository crawling process.
This is our application service layer that coordinates between infrastructure and domain.
"""
import asyncio
from typing import Optional
from src.config import Config
from src.infrastructure.database import RepositoryDatabase
from src.infrastructure.github_client import GitHubClient


class CrawlerService:
    """
    High-level service that orchestrates the crawling process.
    Follows single responsibility principle - just coordinates the crawl.
    """
    
    def __init__(self, database: RepositoryDatabase, github_client: GitHubClient):
        self.database = database
        self.github_client = github_client
        self.total_saved = 0
        self.total_batches = 0
    
    async def crawl_repositories(
        self,
        query: str = "stars:>1",
        max_repos: int = 100_000
    ) -> dict:
        """
        Crawl GitHub repositories and save them to the database.
        
        Args:
            query: GitHub search query
            max_repos: Maximum number of repositories to crawl
        
        Returns:
            Dictionary with crawl statistics
        """
        print("\n" + "="*60)
        print(f"🚀 Starting GitHub Repository Crawler")
        print("="*60)
        print(f"📊 Target: {max_repos:,} repositories")
        print(f"🔍 Query: {query}")
        print(f"🗄️  Database: Ready")
        print("="*60 + "\n")
        
        start_count = await self.database.get_repository_count()
        print(f"📈 Repositories in database before crawl: {start_count:,}\n")
        
        try:
            # Stream repositories in batches and save them
            async for batch in self.github_client.search_repositories(
                query=query,
                max_repos=max_repos
            ):
                # Save batch to database
                rows_affected = await self.database.upsert_repositories(batch)
                self.total_saved += len(batch)
                self.total_batches += 1
                
                print(f"💾 Saved batch #{self.total_batches}: "
                      f"{len(batch)} repos ({rows_affected} rows affected) - "
                      f"Total saved: {self.total_saved:,}")
                
                # Optional: Add a small delay between batches to be extra nice to GitHub
                await asyncio.sleep(0.1)
            
            # Final statistics
            final_count = await self.database.get_repository_count()
            
            print("\n" + "="*60)
            print("✅ CRAWL COMPLETE!")
            print("="*60)
            print(f"📊 Total batches processed: {self.total_batches}")
            print(f"📊 Total repositories crawled: {self.total_saved:,}")
            print(f"📊 Repositories in database: {final_count:,}")
            print(f"📊 New repositories added: {final_count - start_count:,}")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'total_crawled': self.total_saved,
                'total_batches': self.total_batches,
                'final_count': final_count,
                'new_repos': final_count - start_count
            }
            
        except Exception as e:
            print(f"\n❌ Crawl failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_crawled': self.total_saved,
                'total_batches': self.total_batches
            }
    
    async def get_statistics(self) -> dict:
        """Get current database statistics."""
        total = await self.database.get_repository_count()
        return {
            'total_repositories': total
        }