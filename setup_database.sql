-- Drop table if exists (for testing)
DROP TABLE IF EXISTS repositories CASCADE;

-- Main repositories table
CREATE TABLE repositories (
    -- Use GitHub's internal ID as primary key (immutable)
    id BIGINT PRIMARY KEY,
    
    -- Human-readable name
    full_name VARCHAR(255) NOT NULL UNIQUE,
    
    -- Star count (what we're tracking)
    star_count INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamps for tracking
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_crawled_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- For future: store raw JSON data if needed
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for efficient queries
CREATE INDEX idx_repositories_full_name ON repositories(full_name);
CREATE INDEX idx_repositories_star_count ON repositories(star_count DESC);
CREATE INDEX idx_repositories_last_crawled ON repositories(last_crawled_at);

-- Function to automatically update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update timestamp
CREATE TRIGGER update_repositories_updated_at 
    BEFORE UPDATE ON repositories 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
