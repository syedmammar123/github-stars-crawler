# GitHub Stars Crawler

A high-performance GitHub repository crawler that collects star counts using GraphQL API and stores them in PostgreSQL.

## Features

- ✅ Crawls 100,000 repositories efficiently
- ✅ Respects GitHub API rate limits with smart waiting
- ✅ Clean architecture with separation of concerns
- ✅ Automated via GitHub Actions
- ✅ Retry mechanisms with exponential backoff
- ✅ Support for both PostgreSQL and SQLite
- ✅ Exports data to CSV and JSON formats

## Architecture Highlights

### Clean Architecture Principles
- **Domain Layer**: Pure business logic (`Repository` entity)
- **Infrastructure Layer**: Database, API clients, external services
- **Service Layer**: Orchestration and coordination
- **Anti-Corruption Layer**: Translates GitHub API to domain model

### Design Patterns
- **Factory Pattern**: Database creation based on configuration
- **Repository Pattern**: Abstract database operations
- **Strategy Pattern**: Swap between SQLite/PostgreSQL
- **Immutability**: Frozen dataclasses for domain entities

## Quick Start

### Prerequisites
- Python 3.11+
- GitHub account (for API token)
- PostgreSQL 15+ (or use SQLite for local testing)

### Local Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd github-stars-crawler

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
export GITHUB_TOKEN='your_github_token_here'
export DB_TYPE='sqlite'  # or 'postgres'

# 5. Run locally (test with small dataset first!)
export REPOS_TO_CRAWL=1000
python -m src.main
```

### Get GitHub Token

1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Select scope: `public_repo`
4. Copy token and set as environment variable

### PostgreSQL Setup (Optional)

```bash
# Start PostgreSQL (using Docker)
docker run --name postgres-crawler \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_crawler \
  -p 5432:5432 \
  -d postgres:15

# Set environment variables
export DB_TYPE=postgres
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=github_crawler
export DB_USER=postgres
export DB_PASSWORD=postgres

# Setup database schema
python setup_postgres.py

# Run crawler
python -m src.main
```

## GitHub Actions

The workflow runs automatically or can be triggered manually:

1. Go to **Actions** tab in your repository
2. Select **GitHub Stars Crawler** workflow
3. Click **Run workflow**

**No additional secrets needed** - uses default `GITHUB_TOKEN`!

### Workflow Steps

1. ✅ Checkout code
2. ✅ Setup Python environment
3. ✅ Install dependencies
4. ✅ Create PostgreSQL tables (`setup_postgres.py`)
5. ✅ **Crawl 100K repositories** (`python -m src.main`)
6. ✅ Export data to CSV/JSON (`export_data.py`)
7. ✅ Upload artifacts

### Download Results

After workflow completes:
- Go to workflow run page
- Download artifacts:
  - `github-stars-csv` - Full dataset in CSV
  - `github-stars-json` - Full dataset in JSON
  - `crawl-summary` - Statistics and top repos

## Configuration

Environment variables (with defaults):

```bash
# GitHub API
GITHUB_TOKEN=<required>

# Database Type
DB_TYPE=sqlite  # or 'postgres'

# PostgreSQL (if DB_TYPE=postgres)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=github_crawler
DB_USER=postgres
DB_PASSWORD=postgres

# SQLite (if DB_TYPE=sqlite)
SQLITE_PATH=github_crawler.db

# Crawler Settings
REPOS_TO_CRAWL=100000
```

## Project Structure

```
github-stars-crawler/
├── .github/
│   └── workflows/
│       └── crawl.yml           # GitHub Actions workflow
├── src/
│   ├── domain/
│   │   └── repository.py       # Domain entity
│   ├── infrastructure/
│   │   ├── database.py         # Abstract database interface
│   │   ├── sqlite_repo.py      # SQLite implementation
│   │   ├── postgres_repo.py    # PostgreSQL implementation
│   │   ├── database_factory.py # Factory for database creation
│   │   ├── github_client.py    # GitHub GraphQL API client
│   │   ├── rate_limiter.py     # Rate limit management
│   │   └── retry.py            # Retry decorator
│   ├── services/
│   │   └── crawler_service.py  # Orchestrates crawling
│   ├── config.py               # Configuration management
│   └── main.py                 # Entry point
├── setup_postgres.py           # Database schema setup
├── export_data.py              # Export to CSV/JSON
├── setup_database.sql          # PostgreSQL schema
├── requirements.txt            # Python dependencies
├── SCALING_ANALYSIS.md         # Scaling to 500M repos
└── README.md                   # This file
```

## Testing

```bash
# Test database operations
python test_database.py

# Test GitHub API client (requires GITHUB_TOKEN)
export GITHUB_TOKEN='your_token'
python test_github_client.py
```

## Rate Limiting

The crawler respects GitHub's rate limits:
- GraphQL API: 5,000 points/hour
- Each query costs ~1 point
- Automatic waiting when limit is low
- Buffer of 100 points kept for safety

For 100K repos:
- Time required: ~2-3 hours (depends on rate limits)
- Batches: 1,000 batches of 100 repos each

## Database Schema

### Current Schema (100K repos)

```sql
CREATE TABLE repositories (
    id BIGINT PRIMARY KEY,              -- GitHub's internal ID
    full_name VARCHAR(255) UNIQUE,      -- e.g., "facebook/react"
    star_count INTEGER NOT NULL,        -- Number of stars
    created_at TIMESTAMP,               -- Row created
    updated_at TIMESTAMP,               -- Row updated
    last_crawled_at TIMESTAMP,          -- Last crawl time
    metadata JSONB                      -- Future extensibility
);

-- Indexes for performance
CREATE INDEX idx_repositories_star_count ON repositories(star_count DESC);
CREATE INDEX idx_repositories_last_crawled ON repositories(last_crawled_at);
```

### Efficient Updates

The schema uses `ON CONFLICT` (UPSERT) for efficient updates:
- New repos: INSERT
- Existing repos: UPDATE only `star_count` and `last_crawled_at`
- Minimal rows affected per update

## Scaling Analysis

See [SCALING_ANALYSIS.md](SCALING_ANALYSIS.md) for detailed analysis:

### Scaling to 500M Repositories
- Distributed workers with message queues
- Multiple GitHub tokens for parallel API calls
- Database partitioning by star count
- Incremental updates with priority scheduling
- Caching layer (Redis)
- Time-series database (TimescaleDB)

### Schema Evolution
- Separate tables by update frequency
- Append-only for high-velocity data
- Materialized views for aggregations
- Partition time-series data
- Minimize row updates

## Performance

### Current Performance (100K repos)
- **Crawl time**: ~2-3 hours
- **Throughput**: ~10-15 repos/second
- **Database writes**: 1,000 batch upserts
- **API calls**: 1,000 GraphQL queries

### Optimizations
- Batch inserts (100 repos at a time)
- Connection pooling
- Index-only scans
- Asynchronous I/O
- Smart rate limiting

## Contributing

This is an assignment project, but suggestions are welcome!

## License

MIT License - feel free to use for your own projects

## Acknowledgments

- Built for a software engineering assignment
- Demonstrates clean architecture and software engineering best practices
- Uses GitHub's powerful GraphQL API v4