"""
Export database contents to CSV and JSON formats.
This script dumps the repositories table for GitHub Actions artifacts.
"""
import psycopg2
import csv
import json
import os
import sys
from datetime import datetime


def export_to_csv(cursor, output_file='repositories.csv'):
    """Export repositories to CSV file."""
    print(f"📄 Exporting to CSV: {output_file}")
    
    cursor.execute("""
        SELECT id, full_name, star_count, created_at, updated_at, last_crawled_at
        FROM repositories
        ORDER BY star_count DESC
    """)
    
    rows = cursor.fetchall()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['id', 'full_name', 'star_count', 'created_at', 'updated_at', 'last_crawled_at'])
        
        # Write data
        writer.writerows(rows)
    
    print(f"✅ Exported {len(rows):,} repositories to CSV")
    return len(rows)


def export_to_json(cursor, output_file='repositories.json'):
    """Export repositories to JSON file."""
    print(f"📄 Exporting to JSON: {output_file}")
    
    cursor.execute("""
        SELECT id, full_name, star_count, created_at, updated_at, last_crawled_at
        FROM repositories
        ORDER BY star_count DESC
    """)
    
    rows = cursor.fetchall()
    columns = ['id', 'full_name', 'star_count', 'created_at', 'updated_at', 'last_crawled_at']
    
    # Convert to list of dictionaries
    repositories = []
    for row in rows:
        repo_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                value = value.isoformat()
            repo_dict[col] = value
        repositories.append(repo_dict)
    
    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_count': len(repositories),
            'exported_at': datetime.now().isoformat(),
            'repositories': repositories
        }, f, indent=2)
    
    print(f"✅ Exported {len(rows):,} repositories to JSON")
    return len(rows)


def export_summary(cursor, output_file='summary.txt'):
    """Export summary statistics."""
    print(f"📄 Exporting summary: {output_file}")
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM repositories")
    total_count = cursor.fetchone()[0]
    
    # Get star statistics
    cursor.execute("""
        SELECT 
            MIN(star_count) as min_stars,
            MAX(star_count) as max_stars,
            AVG(star_count) as avg_stars,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY star_count) as median_stars
        FROM repositories
    """)
    stats = cursor.fetchone()
    
    # Get top 10 repositories
    cursor.execute("""
        SELECT full_name, star_count
        FROM repositories
        ORDER BY star_count DESC
        LIMIT 10
    """)
    top_repos = cursor.fetchall()
    
    # Write summary
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("GitHub Stars Crawler - Summary Report\n")
        f.write("="*60 + "\n\n")
        f.write(f"Export Date: {datetime.now().isoformat()}\n")
        f.write(f"Total Repositories: {total_count:,}\n\n")
        
        f.write("Star Count Statistics:\n")
        f.write(f"  Minimum:  {stats[0]:,}\n")
        f.write(f"  Maximum:  {stats[1]:,}\n")
        f.write(f"  Average:  {stats[2]:,.2f}\n")
        f.write(f"  Median:   {stats[3]:,.2f}\n\n")
        
        f.write("Top 10 Most Starred Repositories:\n")
        for i, (name, stars) in enumerate(top_repos, 1):
            f.write(f"  {i:2d}. {name:40s} - {stars:,} ⭐\n")
        
        f.write("\n" + "="*60 + "\n")
    
    print(f"✅ Summary exported")


def main():
    """Main export function."""
    
    print("\n" + "="*60)
    print("📦 Exporting Database Contents")
    print("="*60 + "\n")
    
    # Get database connection info from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'github_crawler')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    
    connection_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(connection_url)
        cursor = conn.cursor()
        
        print(f"✅ Connected to database: {db_host}:{db_port}/{db_name}\n")
        
        # Export to different formats
        csv_count = export_to_csv(cursor)
        json_count = export_to_json(cursor)
        export_summary(cursor)
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Export complete!")
        print("="*60)
        print(f"📊 Total repositories exported: {csv_count:,}")
        print("\nGenerated files:")
        print("  - repositories.csv")
        print("  - repositories.json")
        print("  - summary.txt")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)