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
        use_rest_api: bool = False  # CHANGED: Default to GraphQL as per assignment
    ) -> dict:
        """
        Crawl GitHub repositories and save them to the database.
        Uses GraphQL API with partitioned queries to overcome 1K result limit.
        
        Args:
            queries: List of GitHub search queries (for GraphQL mode)
            max_repos: Maximum number of repositories to crawl across all queries
            use_rest_api: Use REST API (True) or GraphQL (False)
        
        Returns:
            Dictionary with crawl statistics
        """
        if queries is None:
            queries = self._get_optimized_queries_for_100k()
        
        print("\n" + "="*60)
        print(f"🚀 Starting GitHub Repository Crawler")
        print("="*60)
        print(f"📊 Target: {max_repos:,} repositories")
        print(f"🔍 API: {'REST' if use_rest_api else 'GraphQL (as required)'}")
        print(f"🔍 Query strategy: {len(queries)} partitioned queries")
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
                # GraphQL - partitioned queries to overcome 1K limit per query
                # Each query can fetch up to 1K repos, so we need 100+ queries for 100K repos
                repos_per_query = 1000  # Max per GraphQL search query
                
                for idx, query in enumerate(queries, 1):
                    if self.total_saved >= max_repos:
                        print(f"\n✅ Reached target of {max_repos:,} repos, stopping...")
                        break
                    
                    remaining = max_repos - self.total_saved
                    query_limit = min(repos_per_query, remaining)
                    
                    print(f"\n📍 Query {idx}/{len(queries)}: {query}")
                    print(f"   Target for this query: {query_limit:,} repos")
                    print(f"   Overall progress: {self.total_saved:,}/{max_repos:,}\n")
                    
                    query_repos = 0
                    async for batch in self.github_client.search_repositories(
                        query=query,
                        max_repos=query_limit
                    ):
                        rows_affected = await self.database.upsert_repositories(batch)
                        self.total_saved += len(batch)
                        query_repos += len(batch)
                        self.total_batches += 1
                        
                        progress_pct = int(100 * self.total_saved / max_repos)
                        print(f"💾 Batch #{self.total_batches}: "
                              f"{len(batch)} repos ({rows_affected} rows affected) - "
                              f"Query total: {query_repos:,} | "
                              f"Overall: {self.total_saved:,}/{max_repos:,} ({progress_pct}%)")
                        
                        # Small delay between batches
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
    
    def _get_optimized_queries_for_100k(self) -> list:
        """
        Get optimized partitioned queries to fetch 100K repos.
        Each query can return max 1K repos (GraphQL limitation).
        
        Strategy: Partition by star count ranges to distribute load evenly.
        We need 100+ queries to get 100K repos.
        """
        queries = []
        
        # Very low star counts (0-10 stars): Many repos, need fine partitioning
        for i in range(0, 11):
            queries.append(f"stars:{i}")
        
        # Low star counts (11-100): 10-repo ranges
        for start in range(11, 101, 10):
            end = start + 9
            queries.append(f"stars:{start}..{end}")
        
        # Medium star counts (101-1000): 50-repo ranges
        for start in range(101, 1001, 50):
            end = start + 49
            queries.append(f"stars:{start}..{end}")
        
        # Higher star counts (1001-10000): 500-repo ranges
        for start in range(1001, 10001, 500):
            end = start + 499
            queries.append(f"stars:{start}..{end}")
        
        # Very high star counts (10001+): 1000-repo ranges
        for start in range(10001, 50001, 1000):
            end = start + 999
            queries.append(f"stars:{start}..{end}")
        
        # Extremely high star counts
        queries.extend([
            "stars:50001..75000",
            "stars:75001..100000",
            "stars:>100000"
        ])
        
        print(f"📋 Generated {len(queries)} partitioned queries to fetch 100K repos")
        return queries
    
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