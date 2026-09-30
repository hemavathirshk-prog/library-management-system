import os
import sys
import mysql.connector
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(os.path.join(project_root, 'backend'))

from config import Config

def init_database():
    """
    Connect to MySQL server, create database 'library_db' if needed,
    and execute the library_management.sql script cleanly.
    """
    print(f"Connecting to MySQL server at {Config.DB_HOST}:{Config.DB_PORT} as user '{Config.DB_USER}'...")
    
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            autocommit=True
        )
    except mysql.connector.Error as err:
        print(f"\n[ERROR] Connection to MySQL failed: {err}")
        return False

    cursor = conn.cursor()
    sql_file = os.path.join(current_dir, 'library_management.sql')
    if not os.path.isfile(sql_file):
        print(f"[ERROR] SQL file not found: {sql_file}")
        return False

    print(f"Reading SQL file: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Clean comments and parse statements safely
    clean_lines = [l for l in text.splitlines() if not l.strip().startswith('--') and not l.strip().startswith('#')]
    clean_text = '\n'.join(clean_lines)
    statements = [s.strip() for s in clean_text.split(';') if s.strip()]

    print(f"Executing {len(statements)} SQL statements...")
    try:
        for stmt in statements:
            cursor.execute(stmt)
        print(">>> SUCCESS: Database 'library_db' and tables created with demo data successfully!")
        return True
    except mysql.connector.Error as err:
        print(f"\n[ERROR] Error executing SQL: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    load_dotenv(os.path.join(project_root, '.env'), override=True)
    success = init_database()
    sys.exit(0 if success else 1)
