import asyncio
from src.config import Config
from src.infrastructure.github_client import GitHubClient

async def test_github_client():
    """Test GitHub API client."""
    
    print("\n" + "="*50)
    print("Testing GitHub API Client")
    print("="*50 + "\n")
    
    # Load config from environment
    config = Config.from_env()
    
    # Check if token is set
    if not config.github_token:
        print("❌ GITHUB_TOKEN not set!")
        print("   Please set it: export GITHUB_TOKEN='your_token_here'")
        print("   Get a token from: https://github.com/settings/tokens")
        return
    
    # Create client
    client = GitHubClient(config)
    
    # Test 1: Get rate limit status
    print("📊 Checking rate limit status...")
    rate_limit = await client.get_rate_limit_status()
    print(f"   Limit: {rate_limit['limit']}")
    print(f"   Remaining: {rate_limit['remaining']}")
    print(f"   Resets at: {rate_limit['resetAt']}\n")
    
    # Test 2: Fetch a small number of repositories
    print("🔍 Fetching 100 repositories (1 batch)...\n")
    
    total_repos = 0
    async for batch in client.search_repositories(query="stars:>1000", max_repos=100):
        total_repos += len(batch)
        
        # Show first 5 repos from first batch
        if total_repos <= 100:
            print("\n📝 Sample repositories:")
            for repo in batch[:5]:
                print(f"   - {repo.full_name}: {repo.star_count:,} ⭐")
    
    print(f"\n✅ Test complete! Fetched {total_repos} repositories")

if __name__ == "__main__":
    asyncio.run(test_github_client())