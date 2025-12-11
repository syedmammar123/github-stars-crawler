"""
Database setup script - Creates PostgreSQL tables and schema.
This script reads setup_database.sql and executes it.
"""
import psycopg2
import os
import sys


def setup_postgres():
    """Setup PostgreSQL database with schema from SQL file."""
    
    print("\n" + "="*60)
    print("🗄️  PostgreSQL Database Setup")
    print("="*60 + "\n")
    
    # Get database connection info from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'github_crawler')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    
    connection_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print(f"📍 Connecting to: {db_host}:{db_port}/{db_name}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(connection_url)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Read SQL setup file
        sql_file = 'setup_database.sql'
        
        if not os.path.exists(sql_file):
            print(f"❌ SQL file not found: {sql_file}")
            return 1
        
        print(f"📖 Reading SQL file: {sql_file}")
        
        with open(sql_file, 'r') as f:
            sql_script = f.read()
        
        # Execute SQL script
        print("⚙️  Executing SQL script...")
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ Tables created successfully")
        
        # Verify tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Verify indexes exist
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        
        indexes = cursor.fetchall()
        print(f"\n📇 Indexes created:")
        for index in indexes:
            print(f"   - {index[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Database setup complete!")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = setup_postgres()
    sys.exit(exit_code)