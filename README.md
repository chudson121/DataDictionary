# MySQL Data Dictionary Generator

A Python script that automatically connects to MySQL servers and generates comprehensive documentation for all databases, tables, and columns in markdown format.

## 🚀 Features

- **Automated Documentation**: Generates detailed markdown files for every table in your MySQL databases
- **Comprehensive Schema Information**: Captures column names, data types, constraints, keys, and defaults
- **Sample Data**: Includes the latest 5 rows from each table for context
- **Environment Variable Configuration**: Secure credential management without hardcoded passwords
- **Database Filtering**: Process only specific databases you care about
- **Smart Data Retrieval**: Intelligently orders sample data by primary keys or auto-increment columns
- **System Database Exclusion**: Automatically skips MySQL system databases
- **Error Handling**: Robust error handling with detailed logging
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 📋 Prerequisites

- Python 3.6+
- MySQL server access
- Required Python packages:

  ```bash
  pip install mysql-connector-python python-dotenv
  ```

## 🛠️ Installation

1. **Clone or download the script**

   ```bash
   git clone <repository-url>
   cd mysql-data-dictionary
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:

   ```bash
   pip install mysql-connector-python python-dotenv
   ```

## ⚙️ Configuration

The script uses environment variables for configuration. You have several options:

### Option 1: .env File (Recommended)

Create a `.env` file in the same directory as the script:

```env
# Required
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password

# Optional (with defaults)
MYSQL_HOST=localhost
MYSQL_PORT=3306
OUTPUT_DIR=data_dictionary

# Optional - Process only specific databases
MYSQL_DATABASE_FILTER=ecommerce,analytics,user_data
```

### Option 2: System Environment Variables

```bash
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_HOST=your_server.com
export MYSQL_PORT=3306
export OUTPUT_DIR=/path/to/documentation
export MYSQL_DATABASE_FILTER=db1,db2,db3
```

### Option 3: Docker Environment

```bash
docker run -e MYSQL_USER=user \
           -e MYSQL_PASSWORD=pass \
           -e MYSQL_HOST=db.example.com \
           -e OUTPUT_DIR=/docs \
           your-container
```

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MYSQL_USER` | ✅ Yes | - | MySQL username |
| `MYSQL_PASSWORD` | ✅ Yes | - | MySQL password |
| `MYSQL_HOST` | ❌ No | `localhost` | MySQL server hostname |
| `MYSQL_PORT` | ❌ No | `3306` | MySQL server port |
| `OUTPUT_DIR` | ❌ No | `data_dictionary` | Output directory for markdown files |
| `MYSQL_DATABASE_FILTER` | ❌ No | All databases | Comma-separated list of databases to process |

## 🚀 Usage

### Basic Usage

```bash
python mysql_data_dictionary.py
```

### With Custom Environment

```bash
# Set variables and run
export MYSQL_USER=admin
export MYSQL_PASSWORD=secretpass
export MYSQL_HOST=prod-db.company.com
export OUTPUT_DIR=./database-docs
python mysql_data_dictionary.py
```

### Docker Usage

```bash
# Using environment file
docker run --env-file .env -v $(pwd)/docs:/app/docs python:3.9 python mysql_data_dictionary.py

# Using direct environment variables
docker run -e MYSQL_USER=admin \
           -e MYSQL_PASSWORD=pass \
           -e MYSQL_HOST=host.docker.internal \
           -v $(pwd)/docs:/app/docs \
           python:3.9 python mysql_data_dictionary.py
```

### CI/CD Pipeline Example (GitHub Actions)

```yaml
name: Generate Database Documentation
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly at 2 AM on Sunday

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install mysql-connector-python python-dotenv
      
      - name: Generate documentation
        env:
          MYSQL_USER: ${{ secrets.MYSQL_USER }}
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_HOST: ${{ secrets.MYSQL_HOST }}
          OUTPUT_DIR: ./database-docs
        run: python mysql_data_dictionary.py
      
      - name: Commit documentation
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add database-docs/
          git commit -m "Update database documentation" || exit 0
          git push
```

## 📁 Output Structure

The script generates markdown files with the naming convention: `DatabaseName.TableName.md`

### Example Output Files

```markdown

data_dictionary/
├── ecommerce.users.md
├── ecommerce.products.md
├── ecommerce.orders.md
├── analytics.page_views.md
└── analytics.user_sessions.md

```

### Sample Generated Markdown

```markdown
# ecommerce.users

**Generated on:** 2025-06-25 14:30:22

## Table Information

**Database:** ecommerce  
**Table Name:** users  
**Description:** User account information  
**Total Rows:** 15,432

## Column Information

| Column Name | Data Type | Nullable | Key | Default | Extra |
|-------------|-----------|----------|-----|---------|-------|
| id | int(11) | No | PRI | - | auto_increment |
| username | varchar(50) | No | UNI | - | - |
| email | varchar(100) | No | UNI | - | - |
| created_at | timestamp | No | - | CURRENT_TIMESTAMP | - |
| is_active | tinyint(1) | No | - | 1 | - |

## Sample Data (Latest 5 rows)

| id | username | email | created_at | is_active |
|----|----------|-------|------------|-----------|
| 15432 | john_doe | john@example.com | 2025-06-25 10:15:30 | 1 |
| 15431 | jane_smith | jane@example.com | 2025-06-25 09:45:12 | 1 |
...
```

## 🔍 Advanced Usage Examples

### Process Only Specific Databases

```bash
export MYSQL_DATABASE_FILTER=production,analytics
python mysql_data_dictionary.py
```

### Custom Output Directory

```bash
export OUTPUT_DIR=/project/database-documentation
python mysql_data_dictionary.py
```

### Remote Database Connection

```bash
export MYSQL_HOST=db.production.company.com
export MYSQL_PORT=3307
export MYSQL_USER=readonly_user
export MYSQL_PASSWORD=secure_password
python mysql_data_dictionary.py
```

### Automated Daily Documentation

Create a cron job:

```bash
# Edit crontab
crontab -e

# Add daily execution at 2 AM
0 2 * * * cd /path/to/script && /usr/bin/python3 mysql_data_dictionary.py >> /var/log/db-docs.log 2>&1
```

## 🛡️ Security Best Practices

1. **Never commit credentials** to version control
2. **Use read-only database users** when possible
3. **Restrict database access** to only necessary databases
4. **Use strong passwords** and rotate them regularly
5. **Consider using database connection pooling** for production environments

### Creating a Read-Only User

```sql
-- Create a dedicated read-only user for documentation
CREATE USER 'docs_generator'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON *.* TO 'docs_generator'@'%';
GRANT SHOW DATABASES ON *.* TO 'docs_generator'@'%';
FLUSH PRIVILEGES;
```

## 🐛 Troubleshooting

### Common Issues

**Connection Refused**

```
Error connecting to MySQL: 2003 (HY000): Can't connect to MySQL server
```

- Check if MySQL server is running