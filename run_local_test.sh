#!/bin/bash
# Local testing script - Run a small crawl to verify everything works

echo "======================================"
echo "GitHub Stars Crawler - Local Test"
echo "======================================"
echo ""

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERROR: GITHUB_TOKEN is not set!"
    echo ""
    echo "Please set your GitHub token:"
    echo "  export GITHUB_TOKEN='your_token_here'"
    echo ""
    echo "Get a token from: https://github.com/settings/tokens"
    echo "Required scope: public_repo"
    exit 1
fi

echo "✅ GitHub token found"
echo ""

# Set test environment variables
export DB_TYPE=sqlite
export SQLITE_PATH=test_crawler.db
export REPOS_TO_CRAWL=500

echo "Test Configuration:"
echo "  Database: SQLite (test_crawler.db)"
echo "  Repositories to crawl: 500"
echo ""

# Clean up old test database
if [ -f "test_crawler.db" ]; then
    echo "🗑️  Removing old test database..."
    rm test_crawler.db
fi

# Run the crawler
echo "🚀 Starting crawler..."
echo ""
python -m src.main

# Check if it succeeded
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✅ Test completed successfully!"
    echo "======================================"
    echo ""
    echo "Test database created: test_crawler.db"
    echo ""
    echo "Next steps:"
    echo "  1. Review the output above"
    echo "  2. If successful, commit your changes"
    echo "  3. Push to GitHub to trigger the workflow"
    echo "  4. Set REPOS_TO_CRAWL=100000 in GitHub Actions"
    echo ""
else
    echo ""
    echo "======================================"
    echo "❌ Test failed!"
    echo "======================================"
    echo ""
    echo "Please check the error messages above."
    exit 1
fi