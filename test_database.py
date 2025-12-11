import asyncio
from src.config import Config, DatabaseType
from src.infrastructure.database_factory import create_database
from src.domain.repository import Repository
from datetime import datetime

async def test_database():
    """Test database operations."""
    
    # Test SQLite
    print("\n" + "="*50)
    print("Testing SQLite")
    print("="*50)
    
    config = Config(
        github_token="dummy",
        db_type=DatabaseType.SQLITE,
        sqlite_path="test.db"
    )
    
    db = create_database(config)
    
    # Setup
    await db.setup()
    
    # Create test repositories
    test_repos = [
        Repository(
            id=1,
            full_name="facebook/react",
            star_count=50000,
            last_crawled_at=datetime.now()
        ),
        Repository(
            id=2,
            full_name="microsoft/vscode",
            star_count=40000,
            last_crawled_at=datetime.now()
        )
    ]
    
    # Insert
    rows = await db.upsert_repositories(test_repos)
    print(f"✅ Inserted {rows} repositories")
    
    # Count
    count = await db.get_repository_count()
    print(f"✅ Total repositories: {count}")
    
    # Update (increase stars)
    test_repos[0] = Repository(
        id=1,
        full_name="facebook/react",
        star_count=51000,  # Updated!
        last_crawled_at=datetime.now()
    )
    
    rows = await db.upsert_repositories([test_repos[0]])
    print(f"✅ Updated {rows} repositories")
    
    # Get all
    all_repos = await db.get_all_repositories()
    print(f"✅ Retrieved {len(all_repos)} repositories")
    for repo in all_repos:
        print(f"   - {repo.full_name}: {repo.star_count} stars")
    
    await db.close()
    print("✅ SQLite test completed!\n")

if __name__ == "__main__":
    asyncio.run(test_database())