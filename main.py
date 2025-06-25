#!/usr/bin/env python3
"""
MySQL Data Dictionary Generator

This script connects to a MySQL server and generates markdown documentation
for each table in each database, including schema information and sample data.
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
from datetime import datetime
from dotenv import load_dotenv


class MySQLDataDictionary:
    def __init__(self, host, user, password, port=3306, database_filter=None):
        """
        Initialize the MySQL Data Dictionary generator
        
        Args:
            host (str): MySQL server hostname
            user (str): MySQL username
            password (str): MySQL password
            port (int): MySQL port (default: 3306)
            database_filter (str): Comma-separated list of databases to include (optional)
        """
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database_filter = [db.strip() for db in database_filter.split(',')] if database_filter else None
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish connection to MySQL server"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                autocommit=True
            )
            self.cursor = self.connection.cursor()
            print(f"Successfully connected to MySQL server at {self.host}:{self.port}")
            return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Close MySQL connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("MySQL connection closed")
    
    def get_databases(self):
        """Get list of all databases (excluding system databases)"""
        try:
            self.cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in self.cursor.fetchall()]
            
            # Filter out system databases
            system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
            user_databases = [db for db in databases if db not in system_dbs]
            
            # Apply database filter if specified
            if self.database_filter:
                user_databases = [db for db in user_databases if db in self.database_filter]
                print(f"Applying database filter: {', '.join(self.database_filter)}")
            
            return user_databases
        except Error as e:
            print(f"Error fetching databases: {e}")
            return []
    
    def get_tables(self, database):
        """Get list of tables in a specific database"""
        try:
            self.cursor.execute(f"USE {database}")
            self.cursor.execute("SHOW TABLES")
            tables = [table[0] for table in self.cursor.fetchall()]
            return tables
        except Error as e:
            print(f"Error fetching tables from {database}: {e}")
            return []
    
    def get_table_info(self, database, table):
        """Get detailed information about a table"""
        try:
            self.cursor.execute(f"USE {database}")
            
            # Get column information
            self.cursor.execute(f"DESCRIBE {table}")
            columns = []
            for col in self.cursor.fetchall():
                columns.append({
                    'name': col[0],
                    'type': col[1],
                    'null': col[2],
                    'key': col[3],
                    'default': col[4],
                    'extra': col[5]
                })
            
            # Get table comment/description
            self.cursor.execute(f"""
                SELECT TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table}'
            """)
            result = self.cursor.fetchone()
            table_description = result[0] if result and result[0] else "No description available"
            
            # Get row count
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = self.cursor.fetchone()[0]
            
            return {
                'columns': columns,
                'description': table_description,
                'row_count': row_count
            }
        except Error as e:
            print(f"Error getting table info for {database}.{table}: {e}")
            return None
    
    def get_sample_data(self, database, table, limit=5):
        """Get sample data from the table (latest 5 rows)"""
        try:
            self.cursor.execute(f"USE {database}")
            
            # Try to order by a primary key or auto-increment column for "latest" rows
            # First, check if there's an auto-increment column
            self.cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{database}' 
                AND TABLE_NAME = '{table}' 
                AND EXTRA = 'auto_increment'
            """)
            auto_inc = self.cursor.fetchone()
            
            if auto_inc:
                order_by = f"ORDER BY {auto_inc[0]} DESC"
            else:
                # Try to find a primary key
                self.cursor.execute(f"""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{database}' 
                    AND TABLE_NAME = '{table}' 
                    AND COLUMN_KEY = 'PRI'
                    LIMIT 1
                """)
                primary_key = self.cursor.fetchone()
                
                if primary_key:
                    order_by = f"ORDER BY {primary_key[0]} DESC"
                else:
                    order_by = ""
            
            query = f"SELECT * FROM {table} {order_by} LIMIT {limit}"
            self.cursor.execute(query)
            
            # Get column names
            column_names = [desc[0] for desc in self.cursor.description]
            
            # Get data
            rows = self.cursor.fetchall()
            
            return {
                'columns': column_names,
                'rows': rows
            }
        except Error as e:
            print(f"Error getting sample data for {database}.{table}: {e}")
            return None
    
    def generate_markdown(self, database, table, table_info, sample_data):
        """Generate markdown content for a table"""
        
        # Sanitize filename
        filename = f"{database}.{table}.md"
        
        # Start building markdown content
        md_content = f"""# {database}.{table}

**Generated on:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Table Information

**Database:** {database}  
**Table Name:** {table}  
**Description:** {table_info['description']}  
**Total Rows:** {table_info['row_count']:,}

## Column Information

| Column Name | Data Type | Nullable | Key | Default | Extra |
|-------------|-----------|----------|-----|---------|-------|
"""
        
        # Add column information
        for col in table_info['columns']:
            null_str = "Yes" if col['null'] == 'YES' else "No"
            key_str = col['key'] if col['key'] else "-"
            default_str = str(col['default']) if col['default'] is not None else "-"
            extra_str = col['extra'] if col['extra'] else "-"
            
            md_content += f"| {col['name']} | {col['type']} | {null_str} | {key_str} | {default_str} | {extra_str} |\n"
        
        # Add sample data section
        md_content += f"\n## Sample Data (Latest {len(sample_data['rows'])} rows)\n\n"
        
        if sample_data['rows']:
            # Create table header
            md_content += "| " + " | ".join(sample_data['columns']) + " |\n"
            md_content += "| " + " | ".join(["---"] * len(sample_data['columns'])) + " |\n"
            
            # Add data rows
            for row in sample_data['rows']:
                row_str = []
                for value in row:
                    if value is None:
                        row_str.append("NULL")
                    elif isinstance(value, str):
                        # Escape pipes and truncate long strings
                        escaped = str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                        if len(escaped) > 50:
                            escaped = escaped[:47] + "..."
                        row_str.append(escaped)
                    else:
                        row_str.append(str(value))
                
                md_content += "| " + " | ".join(row_str) + " |\n"
        else:
            md_content += "*No data available*\n"
        
        md_content += f"\n---\n*Documentation generated by MySQL Data Dictionary Generator*\n"
        
        return filename, md_content
    
    def generate_data_dictionary(self, output_dir="data_dictionary"):
        """Generate complete data dictionary for all databases and tables"""
        
        if not self.connect():
            return False
        
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            databases = self.get_databases()
            print(f"Found {len(databases)} user databases: {', '.join(databases)}")
            
            total_tables = 0
            
            for database in databases:
                print(f"\nProcessing database: {database}")
                tables = self.get_tables(database)
                
                if not tables:
                    print(f"  No tables found in {database}")
                    continue
                
                print(f"  Found {len(tables)} tables")
                
                for table in tables:
                    print(f"    Processing table: {table}")
                    
                    # Get table information
                    table_info = self.get_table_info(database, table)
                    if not table_info:
                        print(f"    Error: Could not get info for {table}")
                        continue
                    
                    # Get sample data
                    sample_data = self.get_sample_data(database, table)
                    if not sample_data:
                        print(f"    Warning: Could not get sample data for {table}")
                        sample_data = {'columns': [], 'rows': []}
                    
                    # Generate markdown
                    filename, content = self.generate_markdown(database, table, table_info, sample_data)
                    
                    # Write to file
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"    Created: {filepath}")
                    total_tables += 1
            
            print(f"\nData dictionary generation completed!")
            print(f"Total tables processed: {total_tables}")
            print(f"Files saved to: {os.path.abspath(output_dir)}")
            
            return True
            
        except Exception as e:
            print(f"Error during data dictionary generation: {e}")
            return False
        
        finally:
            self.disconnect()


def main():
    """Main function to run the data dictionary generator"""
    
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    print("MySQL Data Dictionary Generator")
    print("=" * 35)
    
    # Get connection details from environment variables
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    database_filter = os.getenv('MYSQL_DATABASE_FILTER')  # Optional: comma-separated list of databases to include
    output_dir = os.getenv('OUTPUT_DIR', 'data_dictionary')
    
    print(f"Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password) if password else 'Not set'}")
    print(f"  Database Filter: {database_filter if database_filter else 'All databases'}")
    print(f"  Output Directory: {output_dir}")
    
    # Validate required environment variables
    if not user:
        print("\n❌ Error: MYSQL_USER environment variable is required!")
        print("Please set the following environment variables:")
        print("  MYSQL_USER=your_username")
        print("  MYSQL_PASSWORD=your_password")
        print("  MYSQL_HOST=your_host (optional, defaults to localhost)")
        print("  MYSQL_PORT=your_port (optional, defaults to 3306)")
        print("  MYSQL_DATABASE_FILTER=db1,db2,db3 (optional, process only specified databases)")
        print("  OUTPUT_DIR=output_directory (optional, defaults to data_dictionary)")
        return
    
    if not password:
        print("\n❌ Error: MYSQL_PASSWORD environment variable is required!")
        return
    
    # Create generator instance
    generator = MySQLDataDictionary(host, user, password, port, database_filter)
    
    # Generate data dictionary
    success = generator.generate_data_dictionary(output_dir)
    
    if success:
        print("\n✅ Data dictionary generated successfully!")
    else:
        print("\n❌ Failed to generate data dictionary.")


if __name__ == "__main__":
    main()