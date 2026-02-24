import csv
import io
import os
import time
from werkzeug.utils import secure_filename
from db import execute_query

def save_upload(file, folder):
    if not file or file.filename == '':
        return None
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent name collisions
        filename = f"{int(time.time())}_{filename}"
        
        # Ensure path exists (relative to static)
        upload_path = os.path.join('d:/MINI PROJECT/pr/static', 'uploads', folder)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            
        file.save(os.path.join(upload_path, filename))
        return f"/static/uploads/{folder}/{filename}"
    return None

def export_jobs_to_csv(provider_id):
    """
    Exports jobs posted by a specific provider to CSV.
    """
    jobs = execute_query(
        "SELECT title, skill_required, location_city, location_area, job_date, duration_hours, budget, status, created_at "
        "FROM jobs WHERE provider_id = %s",
        (provider_id,)
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Skill', 'City', 'Area', 'Date', 'Duration (Hrs)', 'Budget (₹)', 'Status', 'Posted At'])
    
    for job in jobs:
        writer.writerow([
            job['title'], job['skill_required'], job['location_city'], 
            job['location_area'], job['job_date'], job['duration_hours'],
            job['budget'], job['status'], job['created_at']
        ])
    
    return output.getvalue()

def create_notification(user_id, message):
    """
    Creates an in-app notification for a user.
    """
    execute_query(
        "INSERT INTO notifications (user_id, message, is_read) VALUES (%s, %s, FALSE)",
        (user_id, message),
        commit=True
    )
