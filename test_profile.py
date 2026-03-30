import sys
sys.path.append(r'd:\MINI PROJECT\pr')
from app import app
from db import execute_query

app.config['TESTING'] = True
app.config['LOGIN_DISABLED'] = True

with app.test_client() as client:
    with app.app_context():
        workers = execute_query("SELECT user_id FROM users WHERE role='worker'")
        if workers:
            for w in workers:
                worker_id = w['user_id']
                print(f"Testing worker profile {worker_id}")
                try:
                    response = client.get(f'/worker/profile/{worker_id}')
                    if response.status_code == 500:
                        print(f"Worker {worker_id} crashed with 500!")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
        else:
            print("No workers found.")
