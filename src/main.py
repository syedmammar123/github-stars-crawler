"""
Main entry point for the GitHub Stars Crawler.
This script orchestrates the entire crawling process.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv()
from src.config import Config
from src.infrastructure.database_factory import create_database
from src.infrastructure.github_client import GitHubClient
from src.services.crawler_service import CrawlerService


async def main():
    """Main execution function."""
    
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    print("\n" + "🌟"*30)
    print("   GitHub Stars Crawler")
    print("🌟"*30 + "\n")
    
    # Load configuration
    config = Config.from_env()
    
    # Validate GitHub token
    if not config.github_token:
        print("❌ ERROR: GITHUB_TOKEN environment variable not set!")
        print("\nPlease set your GitHub token:")
        print("  export GITHUB_TOKEN='your_token_here'")
        print("\nGet a token from: https://github.com/settings/tokens")
        print("Required scopes: public_repo (or repo for private repos)")
        return 1
    
    print(f"✅ GitHub token: {'*' * 20}{config.github_token[-4:]}")
    print(f"✅ Target repositories: {config.repos_to_crawl:,}")
    print(f"✅ Database type: {config.db_type.value}")
    
    # Initialize database
    database = create_database(config)
    
    try:
        print("\n📦 Setting up database...")
        await database.setup()
        
        # Initialize GitHub client
        print("🔌 Connecting to GitHub API...")
        github_client = GitHubClient(config)
        
        # Check rate limit before starting
        rate_limit = await github_client.get_rate_limit_status()
        print(f"✅ Rate limit: {rate_limit['remaining']}/{rate_limit['limit']} remaining")
        
        if rate_limit['remaining'] < 100:
            print(f"⚠️  Warning: Low rate limit! Resets at {rate_limit['resetAt']}")
        
        # Initialize crawler service
        crawler = CrawlerService(database, github_client)
        
        # Start crawling
        result = await crawler.crawl_repositories(
            query="stars:>1",  # All repos with at least 1 star
            max_repos=config.repos_to_crawl
        )
        
        # Show final statistics
        stats = await crawler.get_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Total repositories in database: {stats['total_repositories']:,}")
        
        if result['success']:
            print("\n✅ Crawl completed successfully!")
            return 0
        else:
            print(f"\n❌ Crawl failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Crawl interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Always close database connection
        print("\n🔌 Closing database connection...")
        await database.close()
        print("👋 Goodbye!\n")


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)