# Scaling Analysis: From 100K to 500M Repositories

## Current Implementation (100K Repositories)

Our current design handles 100,000 repositories efficiently with:
- Sequential batch processing (100 repos/batch)
- Single GitHub API client with rate limiting
- PostgreSQL with basic indexes
- Upsert operations for updates
- Estimated runtime: ~2-3 hours (depends on rate limits)

## Scaling to 500 Million Repositories

### 1. **Distributed Architecture**

**Current Problem:** Single process can't handle 500M repos in reasonable time.

**Solutions:**
- **Horizontal Partitioning**: Divide repos by star ranges
  - Worker 1: `stars:1..10`
  - Worker 2: `stars:11..100`
  - Worker 3: `stars:101..1000`
  - Worker N: `stars:>100000`
- **Multiple GitHub Tokens**: Distribute rate limits across multiple tokens
- **Kubernetes/Cloud Run**: Deploy workers as containerized services
- **Message Queue**: Use RabbitMQ/SQS for work distribution
  ```
  Coordinator → Queue → [Worker 1, Worker 2, ... Worker N] → Database
  ```

### 2. **Database Optimizations**

**Current Problem:** Single PostgreSQL instance won't scale to 500M rows efficiently.

**Solutions:**

#### A. Partitioning Strategy
```sql
-- Partition by star count ranges
CREATE TABLE repositories (
    id BIGINT,
    full_name VARCHAR(255),
    star_count INTEGER,
    ...
) PARTITION BY RANGE (star_count);

-- Create partitions
CREATE TABLE repos_0_100 PARTITION OF repositories
    FOR VALUES FROM (0) TO (100);

CREATE TABLE repos_100_1k PARTITION OF repositories
    FOR VALUES FROM (100) TO (1000);

CREATE TABLE repos_1k_10k PARTITION OF repositories
    FOR VALUES FROM (1000) TO (10000);
-- ... etc
```

**Benefits:**
- Parallel queries across partitions
- Faster inserts/updates (smaller indexes per partition)
- Easy archival of old data

#### B. Index Optimization
```sql
-- Partial indexes for commonly queried ranges
CREATE INDEX idx_high_star_repos ON repositories(star_count) 
    WHERE star_count > 10000;

-- Covering index to avoid table lookups
CREATE INDEX idx_repo_stars_name ON repositories(star_count DESC) 
    INCLUDE (full_name);
```

#### C. Consider Time-Series Database
- **TimescaleDB**: Excellent for time-series data (daily crawls)
- Automatic partitioning by time
- Efficient retention policies
- Compression for old data

### 3. **API Rate Limiting at Scale**

**Current:** 5,000 points/hour with single token = 50 repos/minute

**At 500M Scale:**
- Need ~167,000 hours with single token (19 years!)
- **Solution**: Use 100+ GitHub tokens
  - Corporate GitHub Enterprise accounts
  - Distributed across multiple apps
  - Rotating token pool
- **Rate Limiter Service**: Centralized Redis-based rate limiter
  ```python
  # Track rate limits across all workers
  redis.hincrby('rate_limits', token_id, -cost)
  ```

### 4. **Incremental Updates**

**Problem:** Crawling 500M repos daily is wasteful.

**Solutions:**
- **Priority Queue**: Update popular repos more frequently
  - High stars (>10K): Daily
  - Medium stars (1K-10K): Weekly
  - Low stars (<1K): Monthly
- **Change Detection**: GitHub webhooks for star events (for subscribed repos)
- **Bloom Filter**: Track which repos need updates
- **Delta Updates**: Only update repos that changed

```sql
-- Track update frequency
ALTER TABLE repositories ADD COLUMN update_priority INTEGER DEFAULT 1;
ALTER TABLE repositories ADD COLUMN next_update_at TIMESTAMP;

-- Smart scheduling
SELECT id, full_name FROM repositories
WHERE next_update_at < NOW()
ORDER BY update_priority DESC
LIMIT 10000;
```

### 5. **Storage Optimizations**

**At 500M scale:**
- ~500GB for basic data (1KB per repo)
- Add metadata → easily 5-10TB

**Solutions:**
- **Compression**: Enable PostgreSQL compression
- **Archive Old Data**: Move stale repos to cold storage (S3)
- **Columnar Storage**: Use Parquet files for analytics
- **Separate OLTP/OLAP**: 
  - PostgreSQL for transactional updates
  - ClickHouse/BigQuery for analytics

### 6. **Caching Layer**

```
API Request → Redis Cache → PostgreSQL
```

- Cache frequently accessed repos
- Cache aggregations (top 100 repos, etc.)
- TTL-based invalidation
- Reduces database load by 80%+

### 7. **Monitoring & Observability**

**Essential at 500M scale:**
- **Prometheus + Grafana**: Track crawl rates, DB performance
- **Distributed Tracing**: OpenTelemetry to debug bottlenecks
- **Dead Letter Queue**: Capture failed crawls for retry
- **Alerting**: PagerDuty for rate limit exhaustion, DB failures

---

## Schema Evolution for Additional Metadata

### Current Schema
```sql
repositories (id, full_name, star_count, created_at, updated_at, last_crawled_at)
```

### Extended Schema Design

#### Principle: **Separate Tables by Update Frequency**

**Why?** A PR can get 10 comments today, 20 tomorrow. Updating the same row repeatedly:
- Bloats the table (PostgreSQL creates new row versions)
- Slows down queries
- Creates write contention

#### Proposed Schema:

```sql
-- Core repo data (rarely changes)
CREATE TABLE repositories (
    id BIGINT PRIMARY KEY,
    full_name VARCHAR(255) UNIQUE,
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- Star counts (changes frequently, small table)
CREATE TABLE repository_metrics (
    repository_id BIGINT PRIMARY KEY REFERENCES repositories(id),
    star_count INTEGER,
    fork_count INTEGER,
    watcher_count INTEGER,
    open_issues_count INTEGER,
    last_updated TIMESTAMP,
    PRIMARY KEY (repository_id)
);

-- Issues (separate table, can grow large)
CREATE TABLE issues (
    id BIGINT PRIMARY KEY,
    repository_id BIGINT REFERENCES repositories(id),
    number INTEGER,
    title TEXT,
    state VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    comment_count INTEGER DEFAULT 0,
    INDEX idx_repo_issues (repository_id, state, created_at)
);

-- Comments (time-series data, partition by created_at)
CREATE TABLE issue_comments (
    id BIGINT PRIMARY KEY,
    issue_id BIGINT REFERENCES issues(id),
    body TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Pull Requests
CREATE TABLE pull_requests (
    id BIGINT PRIMARY KEY,
    repository_id BIGINT REFERENCES repositories(id),
    number INTEGER,
    title TEXT,
    state VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    merged_at TIMESTAMP,
    comment_count INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    commit_count INTEGER DEFAULT 0,
    INDEX idx_repo_prs (repository_id, state, created_at)
);

-- PR Reviews (frequent updates)
CREATE TABLE pull_request_reviews (
    id BIGINT PRIMARY KEY,
    pull_request_id BIGINT REFERENCES pull_requests(id),
    state VARCHAR(20),
    submitted_at TIMESTAMP,
    INDEX idx_pr_reviews (pull_request_id, submitted_at)
);

-- CI Checks (very frequent, partition by created_at)
CREATE TABLE ci_checks (
    id BIGINT PRIMARY KEY,
    pull_request_id BIGINT REFERENCES pull_requests(id),
    check_name VARCHAR(255),
    status VARCHAR(50),
    conclusion VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_pr_checks (pull_request_id, started_at)
) PARTITION BY RANGE (started_at);
```

### Update Strategy: Minimize Row Modifications

#### Problem: PR gets 10 comments today, 20 tomorrow
**Bad approach:**
```sql
-- This updates the entire PR row twice (inefficient!)
UPDATE pull_requests SET comment_count = 10 WHERE id = 123;
UPDATE pull_requests SET comment_count = 20 WHERE id = 123;
```

**Good approach:**
```sql
-- Only insert new comments (append-only)
INSERT INTO pr_comments (pr_id, body, created_at) VALUES (123, 'New comment', NOW());

-- Update aggregate count separately (single row)
UPDATE pull_requests SET comment_count = (
    SELECT COUNT(*) FROM pr_comments WHERE pr_id = 123
) WHERE id = 123;

-- Even better: Materialized view with incremental refresh
CREATE MATERIALIZED VIEW pr_comment_counts AS
SELECT pr_id, COUNT(*) as count
FROM pr_comments
GROUP BY pr_id;

REFRESH MATERIALIZED VIEW CONCURRENTLY pr_comment_counts;
```

### Efficient Update Patterns

#### 1. **Append-Only for High-Frequency Data**
```sql
-- Don't update existing rows, just append new ones
INSERT INTO ci_checks (pr_id, check_name, status, started_at) 
VALUES (456, 'tests', 'in_progress', NOW());
```

#### 2. **Aggregation Tables (Materialized Views)**
```sql
-- Pre-compute expensive aggregations
CREATE MATERIALIZED VIEW repo_statistics AS
SELECT 
    r.id,
    r.full_name,
    COUNT(DISTINCT i.id) as issue_count,
    COUNT(DISTINCT pr.id) as pr_count,
    COUNT(DISTINCT ic.id) as comment_count
FROM repositories r
LEFT JOIN issues i ON r.id = i.repository_id
LEFT JOIN pull_requests pr ON r.id = pr.repository_id
LEFT JOIN issue_comments ic ON i.id = ic.issue_id
GROUP BY r.id, r.full_name;

-- Refresh incrementally (only changed repos)
REFRESH MATERIALIZED VIEW CONCURRENTLY repo_statistics;
```

#### 3. **Batch Updates with UPSERT**
```sql
-- Update many repos at once (efficient bulk operation)
INSERT INTO repository_metrics (repository_id, star_count, last_updated)
VALUES 
    (1, 50000, NOW()),
    (2, 40000, NOW()),
    (3, 30000, NOW())
ON CONFLICT (repository_id) DO UPDATE SET
    star_count = EXCLUDED.star_count,
    last_updated = EXCLUDED.last_updated;
```

#### 4. **Partitioning by Time for Immutable Data**
```sql
-- Comments are immutable after creation
-- Partition by month for easy archival
CREATE TABLE comments_2025_01 PARTITION OF comments
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Archive old partitions to S3
-- Keeps hot data small and fast
```

### Indexing Strategy

```sql
-- Composite indexes for common queries
CREATE INDEX idx_repo_state_date ON issues(repository_id, state, created_at DESC);
CREATE INDEX idx_pr_state_merged ON pull_requests(repository_id, state, merged_at DESC);

-- Partial indexes (smaller, faster)
CREATE INDEX idx_open_issues ON issues(repository_id, created_at)
    WHERE state = 'open';

-- Expression indexes
CREATE INDEX idx_recent_activity ON repositories((updated_at > NOW() - INTERVAL '30 days'))
    WHERE updated_at > NOW() - INTERVAL '30 days';
```

---

## Summary: Key Principles

### For 500M Repositories:
1. **Horizontal scaling** with distributed workers
2. **Multiple GitHub tokens** for parallel API calls
3. **Database partitioning** by star count or time
4. **Incremental updates** with priority scheduling
5. **Caching layer** to reduce database load

### For Metadata Evolution:
1. **Separate tables by update frequency** (hot/cold data)
2. **Append-only for high-velocity data** (comments, checks)
3. **Materialized views for aggregations** (counts, stats)
4. **Partition time-series data** for easy archival
5. **Minimize row updates** - prefer inserts + aggregation

### Efficiency Metrics:
- **Current**: 1 row updated = 1 write operation
- **Optimized**: 20 new comments = 20 inserts (no updates to PR row!)
- **Result**: 10-100x faster writes, minimal bloat, better concurrency