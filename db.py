import mysql.connector
from mysql.connector import Error
from flask import current_app, g
from config import Config

def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                use_pure=True  # Force Pure Python implementation to prevent crashes
            )
        except Error as e:
            print(f"DATABASE CONNECTION ERROR: {e}")
            return None # Return None and let execute_query handle it
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)

def execute_query(query, params=(), commit=False):
    db = get_db()
    if db is None:
        print("DATABASE ERROR: Cannot execute query because DB connection failed.")
        return None
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        if commit:
            db.commit()
            return cursor.lastrowid
        return cursor.fetchall()
    except Error as e:
        print(f"QUERY ERROR: {e}")
        return None
    finally:
        cursor.close()
