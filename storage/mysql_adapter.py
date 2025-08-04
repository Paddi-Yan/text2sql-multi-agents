"""
MySQL database adapter for schema scanning and data access.
"""
import pymysql
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from utils.models import DatabaseInfo, DatabaseStats
from config.settings import config


class MySQLAdapter:
    """MySQL database adapter for schema operations."""
    
    def __init__(self, db_config=None):
        """Initialize MySQL adapter.
        
        Args:
            db_config: Database configuration, uses global config if None
        """
        self.db_config = db_config or config.database_config
        self._connection = None
    
    def get_connection(self):
        """Get or create database connection."""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                user=self.db_config.username,
                password=self.db_config.password,
                database=self.db_config.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        return self._connection
    
    def close_connection(self):
        """Close database connection."""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None
    
    def scan_database_schema(self, db_name: str) -> Tuple[DatabaseInfo, DatabaseStats]:
        """Scan MySQL database schema.
        
        Args:
            db_name: Database name to scan
            
        Returns:
            Tuple of (DatabaseInfo, DatabaseStats)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get all tables
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """, (db_name,))
            
            tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
            
            desc_dict = {}
            value_dict = {}
            pk_dict = {}
            fk_dict = {}
            
            total_columns = 0
            max_columns = 0
            
            for table_name in tables:
                # Get column information
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        COLUMN_COMMENT,
                        COLUMN_KEY
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (db_name, table_name))
                
                columns_info = cursor.fetchall()
                
                # Extract column descriptions
                columns_desc = []
                primary_keys = []
                
                for col_info in columns_info:
                    col_name = col_info['COLUMN_NAME']
                    col_type = col_info['DATA_TYPE']
                    col_comment = col_info['COLUMN_COMMENT'] or ""
                    
                    columns_desc.append((col_name, col_type, col_comment))
                    
                    if col_info['COLUMN_KEY'] == 'PRI':
                        primary_keys.append(col_name)
                
                desc_dict[table_name] = columns_desc
                pk_dict[table_name] = primary_keys
                
                # Get sample values
                try:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
                    sample_rows = cursor.fetchall()
                    
                    column_values = []
                    for col_info in columns_info:
                        col_name = col_info['COLUMN_NAME']
                        sample_vals = []
                        
                        for row in sample_rows:
                            if col_name in row and row[col_name] is not None:
                                sample_vals.append(str(row[col_name]))
                        
                        column_values.append((col_name, ", ".join(sample_vals[:3])))
                    
                    value_dict[table_name] = column_values
                    
                except Exception as e:
                    # If we can't get sample data, create empty values
                    value_dict[table_name] = [(col[0], "") for col in columns_desc]
                
                # Get foreign keys
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = %s 
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (db_name, table_name))
                
                fk_info = cursor.fetchall()
                
                foreign_keys = []
                for fk in fk_info:
                    from_col = fk['COLUMN_NAME']
                    to_table = fk['REFERENCED_TABLE_NAME']
                    to_col = fk['REFERENCED_COLUMN_NAME']
                    foreign_keys.append((from_col, to_table, to_col))
                
                fk_dict[table_name] = foreign_keys
                
                # Update statistics
                col_count = len(columns_desc)
                total_columns += col_count
                max_columns = max(max_columns, col_count)
            
            # Create DatabaseInfo
            db_info = DatabaseInfo(
                desc_dict=desc_dict,
                value_dict=value_dict,
                pk_dict=pk_dict,
                fk_dict=fk_dict
            )
            
            # Create DatabaseStats
            db_stats = DatabaseStats(
                table_count=len(tables),
                max_column_count=max_columns,
                total_column_count=total_columns,
                avg_column_count=total_columns / len(tables) if tables else 0
            )
            
            return db_info, db_stats
            
        finally:
            cursor.close()
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of result dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return results
        finally:
            cursor.close()
    
    def get_table_names(self, db_name: str) -> List[str]:
        """Get list of table names in database.
        
        Args:
            db_name: Database name
            
        Returns:
            List of table names
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """, (db_name,))
            
            return [row['TABLE_NAME'] for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def table_exists(self, table_name: str, db_name: str) -> bool:
        """Check if table exists in database.
        
        Args:
            table_name: Name of table to check
            db_name: Database name
            
        Returns:
            True if table exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (db_name, table_name))
            
            result = cursor.fetchone()
            return result['count'] > 0
        finally:
            cursor.close()
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table.
        
        Args:
            table_name: Name of table
            
        Returns:
            Number of rows in table
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            result = cursor.fetchone()
            return result['count']
        finally:
            cursor.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_connection()