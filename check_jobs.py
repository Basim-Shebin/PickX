import sys
import os

sys.path.append(r'd:\MINI PROJECT\pr')
from app import app
from db import execute_query

with app.app_context():
    jobs = execute_query("SELECT * FROM jobs ORDER BY job_id DESC LIMIT 5")
    print("Recent jobs:")
    for j in jobs:
        print(j)
