"""
Test MySQL database connection and basic operations.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from config.settings import config


def test_mysql_connection():
    """Test MySQL database connection."""
    print("Testing MySQL connection...")
    print(f"Host: {config.database_config.host}:{config.database_config.port}")
    print(f"User: {config.database_config.username}")
    print(f"Database: {config.database_config.database}")
    
    try:
        # Test connection to MySQL server
        connection = pymysql.connect(
            host=config.database_config.host,
            port=config.database_config.port,
            user=config.database_config.username,
            password=config.database_config.password,
            charset='utf8mb4'
        )
        
        print("✓ Successfully connected to MySQL server")
        
        cursor = connection.cursor()
        
        # Check if database exists
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        
        if config.database_config.database in databases:
            print(f"✓ Database '{config.database_config.database}' exists")
            
            # Connect to specific database
            cursor.execute(f"USE {config.database_config.database}")
            
            # Check tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print(f"✓ Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("⚠ No tables found in database")
                print("Run 'python scripts/init_mysql_db.py' to create sample tables")
        else:
            print(f"⚠ Database '{config.database_config.database}' does not exist")
            print("Run 'python scripts/init_mysql_db.py' to create the database")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"✗ MySQL connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure MySQL server is running")
        print("2. Check the connection details in .env file")
        print("3. Verify the user has proper permissions")
        print("4. Test connection with: mysql -h 127.0.0.1 -P 3306 -u root -p")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_mysql_connection()
    if success:
        print("\n🎉 MySQL connection test passed!")
    else:
        print("\n❌ MySQL connection test failed!")
        sys.exit(1)