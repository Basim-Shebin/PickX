import sys
sys.path.append(r'd:\MINI PROJECT\pr')
from app import app
from db import execute_query

with app.app_context():
    execute_query("ALTER TABLE worker_portfolio CHANGE id post_id INT AUTO_INCREMENT;", commit=True)
    execute_query("ALTER TABLE worker_portfolio CHANGE description caption TEXT NULL;", commit=True)
    execute_query("ALTER TABLE worker_portfolio CHANGE uploaded_at created_at DATETIME DEFAULT CURRENT_TIMESTAMP;", commit=True)
    print("Portfolio table altered successfully")
