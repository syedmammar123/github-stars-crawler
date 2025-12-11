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
        queries: list = None,
        max_repos: int = 100_000,
        use_rest_api: bool = True
    ) -> dict:
        """
        Crawl GitHub repositories and save them to the database.
        Uses REST API by default for better pagination (no 1K limit).
        
        Args:
            queries: List of GitHub search queries (for GraphQL mode)
            max_repos: Maximum number of repositories to crawl across all queries
            use_rest_api: Use REST API (True) or GraphQL (False)
        
        Returns:
            Dictionary with crawl statistics
        """
        if queries is None:
            queries = self._get_default_queries()
        
        print("\n" + "="*60)
        print(f"🚀 Starting GitHub Repository Crawler")
        print("="*60)
        print(f"📊 Target: {max_repos:,} repositories")
        print(f"🔍 API: {'REST (better pagination)' if use_rest_api else 'GraphQL'}")
        print(f"🗄️  Database: Ready")
        print("="*60 + "\n")
        
        start_count = await self.database.get_repository_count()
        print(f"📈 Repositories in database before crawl: {start_count:,}\n")
        
        try:
            if use_rest_api:
                # REST API - single query, better pagination
                print(f"📍 Using REST API search: 'stars:>0'")
                print(f"   Target: {max_repos:,} repos\n")
                
                async for batch in self.github_client.search_repositories_rest(
                    query="stars:>0",
                    max_repos=max_repos
                ):
                    rows_affected = await self.database.upsert_repositories(batch)
                    self.total_saved += len(batch)
                    self.total_batches += 1
                    
                    print(f"💾 Batch #{self.total_batches}: {len(batch)} repos "
                          f"({rows_affected} rows affected) - "
                          f"Total: {self.total_saved:,}/{max_repos:,} "
                          f"({100*self.total_saved//max_repos}% complete)")
                    
                    await asyncio.sleep(0.05)
            else:
                # GraphQL - partitioned queries
                repos_per_query = max_repos // len(queries)
                
                for idx, query in enumerate(queries, 1):
                    print(f"\n📍 Query {idx}/{len(queries)}: {query}")
                    print(f"   Target: {repos_per_query:,} repos\n")
                    
                    async for batch in self.github_client.search_repositories(
                        query=query,
                        max_repos=repos_per_query
                    ):
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
    
    def _get_default_queries(self) -> list:
        """
        Get default partitioned queries by star count ranges.
        Overcomes GitHub search API limit (~1000 results per query).
        """
        return [
            "stars:0..100",
            "stars:101..500",
            "stars:501..1000",
            "stars:1001..5000",
            "stars:5001..10000",
            "stars:10001..50000",
            "stars:50001..100000",
            "stars:>100000"
        ]
    
    async def get_statistics(self) -> dict:
        """Get current database statistics."""
        total = await self.database.get_repository_count()
        return {
            'total_repositories': total
        }