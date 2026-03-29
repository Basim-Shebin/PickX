import sys
sys.path.append(r'd:\MINI PROJECT\pr')
from app import app
from db import execute_query

with app.app_context():
    cols = execute_query("DESCRIBE worker_portfolio")
    print("Columns:")
    for c in cols:
        print(c['Field'])
