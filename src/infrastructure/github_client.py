import asyncio
from typing import List, Optional, AsyncGenerator
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from src.config import Config
from src.domain.repository import Repository
from src.infrastructure.rate_limiter import RateLimiter
from src.infrastructure.retry import async_retry

class GitHubClient:
    """
    GitHub GraphQL API client with rate limiting and retry logic.
    This is our anti-corruption layer - it translates GitHub's API into our domain model.
    """
    
    # GraphQL query to fetch repositories
    SEARCH_REPOSITORIES_QUERY = gql("""
        query SearchRepositories($query: String!, $first: Int!, $after: String) {
            search(query: $query, type: REPOSITORY, first: $first, after: $after) {
                repositoryCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ... on Repository {
                        databaseId
                        nameWithOwner
                        stargazerCount
                        updatedAt
                    }
                }
            }
            rateLimit {
                limit
                remaining
                resetAt
                cost
            }
        }
    """)
    
    def __init__(self, config: Config):
        self.config = config
        self.rate_limiter = RateLimiter()
        
        # Setup GraphQL transport
        transport = AIOHTTPTransport(
            url=config.github_api_url,
            headers={
                'Authorization': f'Bearer {config.github_token}',
                'Accept': 'application/vnd.github.v4+json'
            }
        )
        
        self.client = Client(
            transport=transport,
            fetch_schema_from_transport=False,  # Don't fetch schema (faster)
        )
    
    @async_retry(max_attempts=3, initial_delay=2.0)
    async def _execute_query(
        self,
        query_string: str,
        first: int,
        after: Optional[str] = None
    ) -> dict:
        """
        Execute a GraphQL query with retry logic.
        
        Args:
            query_string: The search query (e.g., "stars:>1")
            first: Number of repositories to fetch
            after: Cursor for pagination
        
        Returns:
            Dict containing search results and rate limit info
        """
        # Wait if rate limit is low
        await self.rate_limiter.wait_if_needed()
        
        # Execute query
        async with self.client as session:
            result = await session.execute(
                self.SEARCH_REPOSITORIES_QUERY,
                variable_values={
                    'query': query_string,
                    'first': first,
                    'after': after
                }
            )
        
        # Update rate limiter with response
        if 'rateLimit' in result:
            self.rate_limiter.update(result['rateLimit'])
        
        return result
    
    async def search_repositories(
        self,
        query: str = "stars:>1",
        max_repos: Optional[int] = None
    ) -> AsyncGenerator[List[Repository], None]:
        """
        Search for repositories and yield them in batches.
        
        Args:
            query: GitHub search query (default: repositories with at least 1 star)
            max_repos: Maximum number of repositories to fetch (None = no limit)
        
        Yields:
            Lists of Repository objects in batches
        """
        cursor = None
        total_fetched = 0
        batch_size = self.config.batch_size
        
        print(f"🔍 Starting repository search: '{query}'")
        print(f"📊 Target: {max_repos if max_repos else 'unlimited'} repositories")
        print(f"📦 Batch size: {batch_size}")
        
        while True:
            # Stop if we've reached the limit
            if max_repos and total_fetched >= max_repos:
                break
            
            # Adjust batch size for last fetch
            if max_repos:
                remaining = max_repos - total_fetched
                batch_size = min(batch_size, remaining)
            
            try:
                # Execute query
                result = await self._execute_query(query, batch_size, cursor)
                
                # Extract repositories
                search_result = result.get('search', {})
                nodes = search_result.get('nodes', [])
                
                if not nodes:
                    print("⚠️  No more repositories found")
                    break
                
                # Convert to domain objects
                repositories = []
                for node in nodes:
                    try:
                        repo = Repository.from_github_response(node)
                        repositories.append(repo)
                    except Exception as e:
                        print(f"⚠️  Failed to parse repository: {e}")
                        continue
                
                total_fetched += len(repositories)
                
                # Yield batch
                if repositories:
                    print(f"✅ Fetched batch: {len(repositories)} repos "
                          f"(total: {total_fetched}) - {self.rate_limiter.get_status()}")
                    yield repositories
                
                # Check pagination
                page_info = search_result.get('pageInfo', {})
                if not page_info.get('hasNextPage'):
                    print("✅ Reached end of search results")
                    break
                
                cursor = page_info.get('endCursor')
                
            except Exception as e:
                print(f"❌ Error fetching repositories: {e}")
                # If retry decorator didn't handle it, we should stop
                break
        
        print(f"🎉 Search complete! Total repositories fetched: {total_fetched}")
    
    async def get_rate_limit_status(self) -> dict:
        """
        Get current rate limit status.
        Useful for monitoring.
        """
        query = gql("""
            query {
                rateLimit {
                    limit
                    remaining
                    resetAt
                    cost
                }
            }
        """)
        
        async with self.client as session:
            result = await session.execute(query)
        
        return result.get('rateLimit', {})