"""
MySQL Data Dictionary Generator

This script connects to a MySQL server and generates markdown documentation
for each table in each database, including schema information and sample data.

Environment Variables (recommended):
    DB_HOST or MYSQL_HOST: MySQL server hostname
    DB_PORT or MYSQL_PORT: MySQL port (default: 3306)
    DB_USER or MYSQL_USER: MySQL username
    DB_PASSWORD or MYSQL_PASSWORD: MySQL password
    OUTPUT_DIR: Output directory for markdown files
    PII_PROTECTION: Enable PII protection (true/false, default: true)

Example .env file:
    DB_HOST=localhost
    DB_PORT=3306
    DB_USER=myuser
    DB_PASSWORD=mypassword
    OUTPUT_DIR=data_dictionary
    PII_PROTECTION=true

Requirements:
    pip install mysql-connector-python python-dotenv
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv


class PIIDetector:
    """Class to detect and mask PII data"""
    
    def __init__(self):
        # Common PII column name patterns
        self.pii_column_patterns = [
            r'.*email.*', r'.*mail.*', r'.*e_mail.*',
            r'.*phone.*', r'.*mobile.*', r'.*tel.*', r'.*fax.*',
            r'.*ssn.*', r'.*social_security.*', r'.*tax_id.*',
            r'.*credit_card.*', r'.*card_number.*', r'.*cc_num.*',
            r'.*password.*', r'.*passwd.*', r'.*pwd.*', r'.*pass.*',
            r'.*license.*', r'.*licence.*', r'.*dl_number.*',
            r'.*passport.*', r'.*visa.*', r'.*identity.*',
            r'.*address.*', r'.*addr.*', r'.*street.*', r'.*zip.*', r'.*postal.*',
            r'.*dob.*', r'.*birth.*', r'.*birthday.*', r'.*age.*',
            r'.*salary.*', r'.*wage.*', r'.*income.*', r'.*earning.*',
            r'.*first_name.*', r'.*last_name.*', r'.*full_name.*', r'.*fname.*', r'.*lname.*',
            r'.*maiden.*', r'.*middle_name.*', r'.*nickname.*',
            r'.*account.*', r'.*routing.*', r'.*iban.*', r'.*swift.*',
            r'.*ip_address.*', r'.*ip_addr.*', r'.*user_agent.*',
            r'.*token.*', r'.*key.*', r'.*secret.*', r'.*api_key.*',
            r'.*signature.*', r'.*fingerprint.*', r'.*hash.*'
        ]
        
        # Regex patterns for data detection
        self.data_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'url': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        }
    
    def is_pii_column(self, column_name):
        """Check if a column name suggests it contains PII"""
        column_lower = column_name.lower()
        return any(re.match(pattern, column_lower, re.IGNORECASE) for pattern in self.pii_column_patterns)
    
    def mask_data_value(self, value, column_name):
        """Mask a data value based on its content and column name"""
        if value is None:
            return None
        
        str_value = str(value)
        
        # If column name suggests PII, mask regardless of content
        if self.is_pii_column(column_name):
            return self._mask_by_column_type(str_value, column_name)
        
        # Check data patterns
        for pattern_name, pattern in self.data_patterns.items():
            if pattern.search(str_value):
                return self._mask_by_pattern(str_value, pattern_name)
        
        return value
    
    def _mask_by_column_type(self, value, column_name):
        """Mask value based on column name patterns"""
        column_lower = column_name.lower()
        
        if any(pattern in column_lower for pattern in ['email', 'mail']):
            return self._mask_email(value)
        elif any(pattern in column_lower for pattern in ['phone', 'mobile', 'tel']):
            return self._mask_phone(value)
        elif any(pattern in column_lower for pattern in ['ssn', 'social_security']):
            return self._mask_ssn(value)
        elif any(pattern in column_lower for pattern in ['password', 'passwd', 'pwd', 'pass']):
            return '[MASKED]'
        elif any(pattern in column_lower for pattern in ['credit_card', 'card_number']):
            return self._mask_credit_card(value)
        elif any(pattern in column_lower for pattern in ['address', 'street']):
            return '[ADDRESS MASKED]'
        elif any(pattern in column_lower for pattern in ['name', 'fname', 'lname']):
            return self._mask_name(value)
        elif any(pattern in column_lower for pattern in ['salary', 'wage', 'income']):
            return '[AMOUNT MASKED]'
        else:
            return '[PII MASKED]'
    
    def _mask_by_pattern(self, value, pattern_name):
        """Mask value based on detected data pattern"""
        if pattern_name == 'email':
            return self._mask_email(value)
        elif pattern_name == 'phone':
            return self._mask_phone(value)
        elif pattern_name == 'ssn':
            return self._mask_ssn(value)
        elif pattern_name == 'credit_card':
            return self._mask_credit_card(value)
        elif pattern_name == 'ip_address':
            return self._mask_ip(value)
        elif pattern_name == 'url':
            return '[URL MASKED]'
        else:
            return '[MASKED]'
    
    def _mask_email(self, email):
        """Mask email address: user@domain.com -> u***@d***.com"""
        if '@' in str(email):
            parts = str(email).split('@')
            if len(parts) == 2:
                user, domain = parts
                if '.' in domain:
                    domain_parts = domain.split('.')
                    masked_domain = domain_parts[0][0] + '***.' + domain_parts[-1]
                else:
                    masked_domain = domain[0] + '***'
                return user[0] + '***@' + masked_domain
        return '[EMAIL MASKED]'
    
    def _mask_phone(self, phone):
        """Mask phone number: 123-456-7890 -> ***-***-7890"""
        phone_str = re.sub(r'\D', '', str(phone))
        if len(phone_str) >= 4:
            return '***-***-' + phone_str[-4:]
        return '[PHONE MASKED]'
    
    def _mask_ssn(self, ssn):
        """Mask SSN: 123-45-6789 -> ***-**-6789"""
        ssn_str = re.sub(r'\D', '', str(ssn))
        if len(ssn_str) == 9:
            return '***-**-' + ssn_str[-4:]
        return '[SSN MASKED]'
    
    def _mask_credit_card(self, cc):
        """Mask credit card: 1234-5678-9012-3456 -> ****-****-****-3456"""
        cc_str = re.sub(r'\D', '', str(cc))
        if len(cc_str) >= 4:
            return '****-****-****-' + cc_str[-4:]
        return '[CARD MASKED]'
    
    def _mask_ip(self, ip):
        """Mask IP address: 192.168.1.100 -> ***.***.***.100"""
        parts = str(ip).split('.')
        if len(parts) == 4:
            return '***.***.***.'+parts[-1]
        return '[IP MASKED]'
    
    def _mask_name(self, name):
        """Mask name: John Doe -> J*** D***"""
        if not name or len(str(name)) < 2:
            return '[NAME MASKED]'
        name_str = str(name).strip()
        if ' ' in name_str:
            parts = name_str.split(' ')
            return ' '.join([part[0] + '***' if len(part) > 1 else part for part in parts])
        else:
            return name_str[0] + '***' if len(name_str) > 1 else '[NAME MASKED]'


class MySQLDataDictionary:
    def __init__(self, host, user, password, port=3306, enable_pii_protection=True):
        """
        Initialize the MySQL Data Dictionary generator
        
        Args:
            host (str): MySQL server hostname
            user (str): MySQL username
            password (str): MySQL password
            port (int): MySQL port (default: 3306)
            enable_pii_protection (bool): Enable PII masking (default: True)
        """
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.connection = None
        self.cursor = None
        self.enable_pii_protection = enable_pii_protection
        self.pii_detector = PIIDetector() if enable_pii_protection else None
        
        if enable_pii_protection:
            print("🛡️  PII Protection: ENABLED")
        else:
            print("⚠️  PII Protection: DISABLED")
        
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
        """Get sample data from the table (latest 5 rows) with PII protection"""
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
            
            # Apply PII protection if enabled
            if self.enable_pii_protection and self.pii_detector:
                protected_rows = []
                pii_columns_found = []
                
                for row in rows:
                    protected_row = []
                    for i, value in enumerate(row):
                        column_name = column_names[i]
                        
                        # Check if this is a PII column
                        if self.pii_detector.is_pii_column(column_name):
                            if column_name not in pii_columns_found:
                                pii_columns_found.append(column_name)
                        
                        # Mask the value
                        masked_value = self.pii_detector.mask_data_value(value, column_name)
                        protected_row.append(masked_value)
                    
                    protected_rows.append(tuple(protected_row))
                
                if pii_columns_found:
                    print(f"    🛡️  PII columns detected and masked: {', '.join(pii_columns_found)}")
                
                rows = protected_rows
            
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
        
        # Check for PII columns in the table schema
        pii_columns = []
        if self.enable_pii_protection and self.pii_detector:
            pii_columns = [col['name'] for col in table_info['columns'] 
                          if self.pii_detector.is_pii_column(col['name'])]
        
        # Start building markdown content
        md_content = f"""# {database}.{table}

**Generated on:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        # Add PII protection notice if applicable
        if self.enable_pii_protection:
            if pii_columns:
                md_content += f"""
🛡️ **PII Protection:** This table contains potentially sensitive columns: {', '.join(pii_columns)}  
Sample data has been masked to protect privacy.
"""
            else:
                md_content += "\n🛡️ **PII Protection:** Enabled (no PII columns detected)\n"
        
        md_content += f"""
## Table Information

**Database:** {database}  
**Table Name:** {table}  
**Description:** {table_info['description']}  
**Total Rows:** {table_info['row_count']:,}

## Column Information

| Column Name | Data Type | Nullable | Key | Default | Extra | PII Risk |
|-------------|-----------|----------|-----|---------|-------|----------|
"""
        
        # Add column information with PII risk assessment
        for col in table_info['columns']:
            null_str = "Yes" if col['null'] == 'YES' else "No"
            key_str = col['key'] if col['key'] else "-"
            default_str = str(col['default']) if col['default'] is not None else "-"
            extra_str = col['extra'] if col['extra'] else "-"
            
            # PII risk assessment
            pii_risk = "⚠️ HIGH" if (self.enable_pii_protection and self.pii_detector and 
                                   self.pii_detector.is_pii_column(col['name'])) else "✅ LOW"
            
            md_content += f"| {col['name']} | {col['type']} | {null_str} | {key_str} | {default_str} | {extra_str} | {pii_risk} |\n"
        
        # Add sample data section
        protection_note = " (PII Protected)" if self.enable_pii_protection else ""
        md_content += f"\n## Sample Data{protection_note} (Latest {len(sample_data['rows'])} rows)\n\n"
        
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
        
        if self.enable_pii_protection:
            md_content += f"\n## PII Protection Summary\n\n"
            md_content += f"- **Protection Status:** Enabled\n"
            md_content += f"- **PII Columns Detected:** {len(pii_columns)}\n"
            if pii_columns:
                md_content += f"- **Protected Columns:** {', '.join(pii_columns)}\n"
            md_content += f"- **Masking Applied:** Data patterns and column names analyzed\n"
        
        md_content += f"\n---\n*Documentation generated by MySQL Data Dictionary Generator with PII Protection*\n"
        
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


def get_db_config():
    """Get database configuration from environment variables or user input"""
    
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Try to get from environment variables first
    host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST')
    port = os.getenv('DB_PORT') or os.getenv('MYSQL_PORT')
    user = os.getenv('DB_USER') or os.getenv('MYSQL_USER')
    password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD')
    output_dir = os.getenv('OUTPUT_DIR')
    pii_protection = os.getenv('PII_PROTECTION', 'true').lower() in ('true', '1', 'yes', 'on')
    
    # Show what we found from environment
    env_found = []
    if host: env_found.append("host")
    if port: env_found.append("port") 
    if user: env_found.append("user")
    if password: env_found.append("password")
    if output_dir: env_found.append("output_dir")
    
    if env_found:
        print(f"Found environment variables for: {', '.join(env_found)}")
    else:
        print("No environment variables found. Using interactive input.")
    
    # Fill in missing values with user input
    if not host:
        host = input("MySQL Host (default: localhost): ").strip() or "localhost"
    else:
        print(f"Using host: {host}")
    
    if not port:
        port = input("MySQL Port (default: 3306): ").strip() or "3306"
    else:
        print(f"Using port: {port}")
    
    if not user:
        user = input("MySQL Username: ").strip()
    else:
        print(f"Using user: {user}")
    
    if not password:
        password = input("MySQL Password: ").strip()
    else:
        print("Using password from environment variable")
    
    if not output_dir:
        output_dir = input("Output Directory (default: data_dictionary): ").strip() or "data_dictionary"
    else:
        print(f"Using output directory: {output_dir}")
    
    # Ask about PII protection if not set in environment
    if 'PII_PROTECTION' not in os.environ:
        pii_input = input("Enable PII Protection? (Y/n): ").strip().lower()
        pii_protection = pii_input not in ('n', 'no', 'false', '0', 'off')
    else:
        print(f"PII Protection: {'Enabled' if pii_protection else 'Disabled'}")
    
    return host, port, user, password, output_dir, pii_protection


def main():
    """Main function to run the data dictionary generator"""
    
    print("MySQL Data Dictionary Generator")
    print("=" * 35)
    print()
    
    # Get connection details from environment or user input
    host, port, user, password, output_dir, pii_protection = get_db_config()
    
    try:
        port = int(port)
    except ValueError:
        print("Invalid port number. Using default port 3306.")
        port = 3306
    
    if not user:
        print("Username is required!")
        return
    
    # Create generator instance
    generator = MySQLDataDictionary(host, user, password, port, pii_protection)
    
    # Generate data dictionary
    success = generator.generate_data_dictionary(output_dir)
    
    if success:
        print("\n✅ Data dictionary generated successfully!")
    else:
        print("\n❌ Failed to generate data dictionary.")


if __name__ == "__main__":
    main()