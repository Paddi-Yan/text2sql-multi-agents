"""
Initialize MySQL database with sample data for testing.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from config.settings import config


def create_sample_database():
    """Create sample database and tables for testing."""
    
    # Connect to MySQL server (without specifying database)
    connection = pymysql.connect(
        host=config.database_config.host,
        port=config.database_config.port,
        user=config.database_config.username,
        password=config.database_config.password,
        charset='utf8mb4'
    )
    
    try:
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.database_config.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {config.database_config.database}")
        
        print(f"Created/Using database: {config.database_config.database}")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                age INT,
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(50),
                country VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                profile_picture_url TEXT,
                bio TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                parent_id INT,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                category_id INT,
                brand VARCHAR(100),
                sku VARCHAR(50) UNIQUE,
                stock_quantity INT DEFAULT 0,
                weight DECIMAL(8,2),
                dimensions VARCHAR(50),
                color VARCHAR(30),
                size VARCHAR(20),
                material VARCHAR(100),
                is_featured BOOLEAN DEFAULT FALSE,
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                order_number VARCHAR(50) UNIQUE NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                total_amount DECIMAL(10,2) NOT NULL,
                shipping_address TEXT,
                billing_address TEXT,
                payment_method VARCHAR(50),
                payment_status VARCHAR(20) DEFAULT 'pending',
                shipping_cost DECIMAL(8,2) DEFAULT 0,
                tax_amount DECIMAL(8,2) DEFAULT 0,
                discount_amount DECIMAL(8,2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                shipped_at TIMESTAMP NULL,
                delivered_at TIMESTAMP NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create order_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL,
                user_id INT NOT NULL,
                rating INT CHECK (rating >= 1 AND rating <= 5),
                title VARCHAR(200),
                comment TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                helpful_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        print("Created all tables successfully!")
        
        # Insert sample data
        print("Inserting sample data...")
        
        # Insert users
        cursor.execute("""
            INSERT IGNORE INTO users (username, email, first_name, last_name, age, city, country) VALUES
            ('john_doe', 'john@example.com', 'John', 'Doe', 30, 'New York', 'USA'),
            ('jane_smith', 'jane@example.com', 'Jane', 'Smith', 25, 'Los Angeles', 'USA'),
            ('bob_johnson', 'bob@example.com', 'Bob', 'Johnson', 35, 'Chicago', 'USA')
        """)
        
        # Insert categories
        cursor.execute("""
            INSERT IGNORE INTO categories (id, name, description) VALUES
            (1, 'Electronics', 'Electronic devices and gadgets'),
            (2, 'Clothing', 'Apparel and fashion items'),
            (3, 'Books', 'Books and educational materials'),
            (4, 'Home & Garden', 'Home improvement and garden supplies')
        """)
        
        # Insert products
        cursor.execute("""
            INSERT IGNORE INTO products (name, description, price, category_id, brand, sku, stock_quantity) VALUES
            ('Laptop Pro 15', 'High-performance laptop with 16GB RAM', 1299.99, 1, 'TechBrand', 'LAPTOP-001', 50),
            ('Wireless Headphones', 'Noise-cancelling wireless headphones', 199.99, 1, 'AudioTech', 'HEADPHONE-001', 100),
            ('Cotton T-Shirt', 'Comfortable cotton t-shirt', 19.99, 2, 'FashionCo', 'TSHIRT-001', 200),
            ('Programming Book', 'Learn Python programming', 39.99, 3, 'TechBooks', 'BOOK-001', 75),
            ('Garden Tools Set', 'Complete set of garden tools', 89.99, 4, 'GardenPro', 'TOOLS-001', 30)
        """)
        
        # Insert orders
        cursor.execute("""
            INSERT IGNORE INTO orders (user_id, order_number, total_amount, status) VALUES
            (1, 'ORD-2024-001', 1299.99, 'completed'),
            (2, 'ORD-2024-002', 219.98, 'shipped'),
            (3, 'ORD-2024-003', 59.98, 'pending')
        """)
        
        # Insert order items
        cursor.execute("""
            INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES
            (1, 1, 1, 1299.99, 1299.99),
            (2, 2, 1, 199.99, 199.99),
            (2, 3, 1, 19.99, 19.99),
            (3, 4, 1, 39.99, 39.99),
            (3, 3, 1, 19.99, 19.99)
        """)
        
        # Insert reviews
        cursor.execute("""
            INSERT IGNORE INTO reviews (product_id, user_id, rating, title, comment) VALUES
            (1, 2, 5, 'Excellent laptop!', 'Very fast and reliable. Great for development work.'),
            (2, 1, 4, 'Good headphones', 'Sound quality is great, but could be more comfortable.'),
            (3, 3, 5, 'Perfect fit', 'Great quality cotton t-shirt. Very comfortable.')
        """)
        
        connection.commit()
        print("Sample data inserted successfully!")
        
        # Show table information
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} rows")
        
    except Exception as e:
        print(f"Error: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    print("Initializing MySQL database...")
    print(f"Host: {config.database_config.host}:{config.database_config.port}")
    print(f"Database: {config.database_config.database}")
    print(f"User: {config.database_config.username}")
    
    create_sample_database()
    print("\nDatabase initialization completed!")