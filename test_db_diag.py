import mysql.connector
from dotenv import load_dotenv
import os
import bcrypt

load_dotenv()

def test_db():
    print("--- PickX DB Test Tool ---")
    host = os.environ.get('MYSQL_HOST', 'localhost')
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', '')
    database = os.environ.get('MYSQL_DB', 'pickx_db')
    
    print(f"Attempting to connect to {database} on {host} as {user}...")
    
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        print("SUCCESS: Connected to database.")
        
        cursor = conn.cursor(dictionary=True)
        
        # Test Query
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print(f"Tables found: {[list(t.values())[0] for t in tables]}")
        
        # Test Bcrypt
        print("Testing bcrypt hashing...")
        hashed = bcrypt.hashpw(b"test_password", bcrypt.gensalt(10))
        print(f"Bcrypt hash: {hashed}")
        
        conn.close()
        print("SUCCESS: All tests passed.")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_db()
