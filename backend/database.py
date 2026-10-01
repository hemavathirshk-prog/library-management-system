import mysql.connector
from mysql.connector import Error
from backend.config import Config

def get_db_connection(use_database=True):
    """
    Establish and return a connection to the MySQL database.
    If use_database is False, connects to the MySQL server without selecting a database.
    """
    try:
        kwargs = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'autocommit': False
        }
        if use_database:
            kwargs['database'] = Config.DB_NAME

        connection = mysql.connector.connect(**kwargs)
        return connection
    except Error as e:
        print(f"[Database Connection Error]: {e}")
        return None

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Helper function to execute parameterized queries safely.
    Prevents SQL injection by enforcing parameterized queries.
    Returns (result, error_message).
    """
    conn = get_db_connection()
    if conn is None:
        return None, "Database connection failed. Please ensure MySQL is running."

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()

        if commit:
            conn.commit()
            result = cursor.lastrowid if cursor.lastrowid else True

        return result, None
    except Error as e:
        if conn:
            conn.rollback()
        print(f"[SQL Execution Error]: {e}")
        return None, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_system_settings():
    """
    Fetch business rule settings from the settings table.
    Ensures fine_per_day, loan_days, and max_renewals are never hardcoded.
    """
    query = "SELECT fine_per_day, loan_days, max_renewals FROM settings LIMIT 1"
    setting, err = execute_query(query, fetch_one=True)
    if setting:
        return {
            'fine_per_day': float(setting['fine_per_day']),
            'loan_days': int(setting['loan_days']),
            'max_renewals': int(setting['max_renewals'])
        }
    # Safe defaults if table is empty
    return {
        'fine_per_day': 5.0,
        'loan_days': 14,
        'max_renewals': 2
    }
