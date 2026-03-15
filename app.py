from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import bcrypt
from config import Config
from db import init_app, execute_query
from utils import export_jobs_to_csv, create_notification
from recommendation import get_recommended_workers
import os
from flask import Response

app = Flask(__name__)
app.config.from_object(Config)

# Standardized Job Categories for matching
JOB_CATEGORIES = [
    "Plumbing", "Electrical Work", "House Cleaning", 
    "Gardening", "Painting", "Construction", 
    "Carpentry", "Loading/Unloading", "AC Repair", "Welding"
]

app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.context_processor
def inject_notification_count():
    if current_user.is_authenticated:
        count = execute_query("SELECT COUNT(*) as c FROM notifications WHERE user_id = %s AND is_read = FALSE", (current_user.id,))
        return dict(unread_count=count[0]['c'] if count else 0)
    return dict(unread_count=0)

# Initialize Database
init_app(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, full_name, role, profile_image):
        self.id = user_id
        self.full_name = full_name
        self.role = role
        self.profile_image = profile_image

@login_manager.user_loader
def load_user(user_id):
    result = execute_query("SELECT user_id, full_name, role, profile_image FROM users WHERE user_id = %s", (user_id,))
    if result:
        return User(result[0]['user_id'], result[0]['full_name'], result[0]['role'], result[0]['profile_image'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user_data = execute_query("SELECT * FROM users WHERE email = %s", (email,))
        if user_data:
            stored_hash = user_data[0]['password_hash']
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                user = User(user_data[0]['user_id'], user_data[0]['full_name'], user_data[0]['role'], user_data[0]['profile_image'])
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        city = request.form['city']
        area = request.form.get('area')
        role = request.form['role']
        
        from utils import save_upload
        profile_img_path = save_upload(request.files.get('profile_image'), 'profiles') or '/static/img/default-profile.png'
        
        # SRS: Salting and hashing with bcrypt (cost factor >= 10 handled by default or specified)
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(10)).decode('utf-8')
        
        try:
            user_id = execute_query(
                "INSERT INTO users (full_name, email, password_hash, phone, role, city, area, profile_image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (full_name, email, hashed_password, phone, role, city, area, profile_img_path),
                commit=True
            )
            
            if role == 'worker':
                # SRS: Workers provide skill, experience, wage during registration
                daily_wage = request.form.get('daily_wage', 0)
                experience_years = request.form.get('experience_years', 0)
                skills = ",".join(request.form.getlist('skills')) # Get multiple selected skills
                execute_query(
                    "INSERT INTO worker_profiles (worker_id, daily_wage, experience_years, skills) VALUES (%s, %s, %s, %s)",
                    (user_id, daily_wage, experience_years, skills),
                    commit=True
                )
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            
    return render_template('register.html', categories=JOB_CATEGORIES)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'provider':
        jobs = execute_query(
            "SELECT j.*, (SELECT booking_id FROM bookings WHERE job_id = j.job_id AND status = 'confirmed' LIMIT 1) as accepted_booking_id "
            "FROM jobs j WHERE provider_id = %s", 
            (current_user.id,)
        )
        return render_template('customer_dashboard.html', jobs=jobs)
    elif current_user.role == 'worker':
        profile = execute_query("SELECT * FROM worker_profiles WHERE worker_id = %s", (current_user.id,))
        profile = profile[0] if profile else None
        
        search_query = request.args.get('q', '').strip()
        
        # SRS: Better matching visibility
        if not profile or not profile.get('skills'):
            flash('Please update your skills in Profile to see matching jobs!', 'info')
            
        if search_query:
            # Get semantic variants for the query
            variants = get_semantic_skills(search_query)
            
            # Construct query with multiple OR conditions for semantic matching
            or_clauses = ["title LIKE %s", "location_city LIKE %s", "location_area LIKE %s"]
            params = [f'%{search_query}%', f'%{search_query}%', f'%{search_query}%']
            
            for variant in variants:
                or_clauses.append("skill_required LIKE %s")
                params.append(f'%{variant}%')
                
            query = f"SELECT * FROM jobs WHERE status = 'open' AND ({' OR '.join(or_clauses)})"
            all_open_jobs = execute_query(query, tuple(params))
        else:
            all_open_jobs = execute_query("SELECT * FROM jobs WHERE status = 'open'")

        recommended_jobs = []
        if profile and profile.get('skills'):
            from recommendation import calculate_recommendation_score
            for job in all_open_jobs:
                score = calculate_recommendation_score(profile, job)
                # If searching, we show all matches but still sort by score
                if search_query or score > 0:
                    job['score'] = score
                    recommended_jobs.append(job)
        recommended_jobs = sorted(recommended_jobs, key=lambda x: x.get('score', 0), reverse=True)
        
        portfolio = execute_query("SELECT * FROM worker_portfolio WHERE worker_id = %s", (current_user.id,))
        
        return render_template('worker_dashboard.html', profile=profile, recommended_jobs=recommended_jobs, search_query=search_query, portfolio=portfolio)
    else:
        return redirect(url_for('admin_dashboard'))

@app.route('/provider/export-jobs')
@login_required
def export_jobs():
    if current_user.role != 'provider':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    csv_data = export_jobs_to_csv(current_user.id)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=my_jobs.csv"}
    )


@app.route('/worker/profile', methods=['GET', 'POST'])
@login_required
def worker_profile():
    if current_user.role != 'worker':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        bio = request.form['bio']
        daily_wage = request.form['daily_wage']
        experience_years = request.form['experience_years']
        availability_status = request.form['availability_status']
        skills = ",".join(request.form.getlist('skills'))
        
        from utils import save_upload
        # Handle Profile Image Update
        new_profile_img = save_upload(request.files.get('profile_image'), 'profiles')
        if new_profile_img:
            execute_query("UPDATE users SET profile_image = %s WHERE user_id = %s", (new_profile_img, current_user.id), commit=True)
            # Update current_user object for immediate UI refresh
            current_user.profile_image = new_profile_img

        # Handle Portfolio Images/Videos - MOVED TO DEDICATED POSTS SECTION
        # portfolio_files = request.files.getlist('portfolio_images')
        # for p_file in portfolio_files:
        #     p_path = save_upload(p_file, 'portfolios')
        #     if p_path:
        #         execute_query("INSERT INTO worker_portfolio (worker_id, image_path) VALUES (%s, %s)", (current_user.id, p_path), commit=True)

        execute_query(
            "UPDATE worker_profiles SET bio=%s, daily_wage=%s, experience_years=%s, availability_status=%s, skills=%s WHERE worker_id=%s",
            (bio, daily_wage, experience_years, availability_status, skills, current_user.id),
            commit=True
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('worker_profile'))

    profile = execute_query("SELECT * FROM worker_profiles WHERE worker_id = %s", (current_user.id,))
    return render_template('worker_profile.html', profile=profile[0] if profile else None, categories=JOB_CATEGORIES)

@app.route('/worker/posts', methods=['GET', 'POST'])
@login_required
def manage_posts():
    if current_user.role != 'worker':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        caption = request.form.get('caption')
        post_file = request.files.get('post_image')
        
        if post_file:
            from utils import save_upload
            p_path = save_upload(post_file, 'portfolios')
            if p_path:
                execute_query(
                    "INSERT INTO worker_portfolio (worker_id, image_path, caption) VALUES (%s, %s, %s)",
                    (current_user.id, p_path, caption),
                    commit=True
                )
                flash('Work picture posted successfully!', 'success')
            else:
                flash('Error uploading image', 'danger')
        else:
            flash('Please select an image to post', 'warning')
        return redirect(url_for('manage_posts'))

    posts = execute_query("SELECT * FROM worker_portfolio WHERE worker_id = %s ORDER BY created_at DESC", (current_user.id,))
    return render_template('worker_posts.html', posts=posts)

@app.route('/worker/post/delete/<int:post_id>')
@login_required
def delete_post(post_id):
    if current_user.role != 'worker':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check ownership
    post = execute_query("SELECT * FROM worker_portfolio WHERE post_id = %s AND worker_id = %s", (post_id, current_user.id))
    if post:
        execute_query("DELETE FROM worker_portfolio WHERE post_id = %s", (post_id,), commit=True)
        flash('Post deleted successfully', 'success')
    else:
        flash('Post not found or unauthorized', 'danger')
    
    return redirect(url_for('manage_posts'))

@app.route('/provider/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.role != 'provider':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        skill_required = request.form['skill_required']
        location_city = request.form['location_city']
        location_area = request.form.get('location_area')
        job_date = request.form['job_date']
        duration_hours = request.form['duration_hours']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        execute_query(
            "INSERT INTO jobs (provider_id, title, skill_required, location_city, location_area, job_date, duration_hours, budget, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (current_user.id, title, skill_required, location_city, location_area, job_date, duration_hours, budget, latitude, longitude),
            commit=True
        )
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('post_job.html', categories=JOB_CATEGORIES)

from utils import save_upload, export_jobs_to_csv, create_notification, get_semantic_skills

@app.route('/provider/search-workers')
@login_required
def search_workers():
    if current_user.role != 'provider':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    job_id = request.args.get('job_id')
    search_query = request.args.get('q', '').strip()
    
    # If job_id is provided, we can pre-fill search with the job's required skill
    if job_id and not search_query:
        job = execute_query("SELECT skill_required FROM jobs WHERE job_id = %s", (job_id,))
        if job:
            search_query = job[0]['skill_required']
    
    if search_query:
        # Get semantic variants for the query
        variants = get_semantic_skills(search_query)
        
        # Construct query with multiple OR conditions for semantic matching
        where_clauses = ["u.role = 'worker'"]
        or_clauses = ["u.full_name LIKE %s", "u.city LIKE %s"]
        params = [f'%{search_query}%', f'%{search_query}%']
        
        for variant in variants:
            or_clauses.append("wp.skills LIKE %s")
            params.append(f'%{variant}%')
            
        where_clauses.append(f"({' OR '.join(or_clauses)})")
        
        query = (
            "SELECT u.*, wp.* FROM users u "
            "JOIN worker_profiles wp ON u.user_id = wp.worker_id "
            f"WHERE {' AND '.join(where_clauses)}"
        )
        workers = execute_query(query, tuple(params))
    else:
        # Show top rated workers by default
        workers = execute_query(
            "SELECT u.*, wp.* FROM users u "
            "JOIN worker_profiles wp ON u.user_id = wp.worker_id "
            "WHERE u.role = 'worker' ORDER BY wp.avg_rating DESC LIMIT 10"
        )
        
    return render_template('search_workers.html', workers=workers, search_query=search_query, job_id=job_id)

@app.route('/worker/profile/<int:worker_id>')
@login_required
def worker_profile_public(worker_id):
    worker = execute_query("SELECT u.*, wp.* FROM users u JOIN worker_profiles wp ON u.user_id = wp.worker_id WHERE u.user_id = %s", (worker_id,))
    if not worker:
        flash('Worker not found', 'danger')
        return redirect(url_for('dashboard'))
    
    portfolio = execute_query("SELECT * FROM worker_portfolio WHERE worker_id = %s", (worker_id,))
    return render_template('worker_profile_public.html', worker=worker[0], portfolio=portfolio)

@app.route('/worker/apply/<int:job_id>')
@login_required
def apply_job(job_id):
    if current_user.role != 'worker':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if already applied
    existing = execute_query(
        "SELECT * FROM bookings WHERE job_id=%s AND worker_id=%s",
        (job_id, current_user.id)
    )
    if existing:
        flash('You have already applied for this job', 'warning')
        return redirect(url_for('dashboard'))

    job = execute_query("SELECT provider_id, title FROM jobs WHERE job_id = %s", (job_id,))
    if not job:
        flash('Job not found', 'danger')
        return redirect(url_for('dashboard'))

    execute_query(
        "INSERT INTO bookings (job_id, worker_id, provider_id) VALUES (%s, %s, %s)",
        (job_id, current_user.id, job[0]['provider_id']),
        commit=True
    )
    
    # Notify provider
    create_notification(job[0]['provider_id'], f"New applicant for your job: {job[0]['title']}")
        
    flash('Application sent successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/provider/job/<int:job_id>/applicants')
@login_required
def view_applicants(job_id):
    if current_user.role != 'provider':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    applicants = execute_query(
        "SELECT b.booking_id, u.user_id, u.full_name, u.profile_image, wp.avg_rating, wp.daily_wage, b.status "
        "FROM bookings b "
        "JOIN users u ON b.worker_id = u.user_id "
        "JOIN worker_profiles wp ON u.user_id = wp.worker_id "
        "WHERE b.job_id = %s",
        (job_id,)
    )
    return render_template('view_applicants.html', applicants=applicants, job_id=job_id)

@app.route('/provider/booking/<int:booking_id>/accept')
@login_required
def accept_worker(booking_id):
    if current_user.role != 'provider':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    booking = execute_query("SELECT job_id, worker_id FROM bookings WHERE booking_id = %s", (booking_id,))
    if booking:
        # Accept this booking
        execute_query("UPDATE bookings SET status='confirmed' WHERE booking_id=%s", (booking_id,), commit=True)
        # Reject others for the same job
        execute_query("UPDATE bookings SET status='cancelled' WHERE job_id=%s AND booking_id!=%s", (booking[0]['job_id'], booking_id), commit=True)
        # Update job status
        execute_query("UPDATE jobs SET status='booked' WHERE job_id=%s", (booking[0]['job_id'],), commit=True)
        
        create_notification(booking[0]['worker_id'], "Your booking request has been confirmed!")
        flash('Worker assigned to job!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/submit-review/<int:booking_id>', methods=['POST'])
@login_required
def submit_review(booking_id):
    score = request.form['score']
    review_text = request.form['review_text']
    
    booking = execute_query("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
    if booking:
        job_id = booking[0]['job_id']
        worker_id = booking[0]['worker_id']
        provider_id = current_user.id
        
        execute_query(
            "INSERT INTO ratings (booking_id, provider_id, worker_id, score, review_text) VALUES (%s, %s, %s, %s, %s)",
            (booking_id, provider_id, worker_id, score, review_text),
            commit=True
        )
        
        # Update worker rating and jobs completed
        avg_data = execute_query(
            "SELECT AVG(score) as avg_s, COUNT(*) as total FROM ratings WHERE worker_id = %s",
            (worker_id,)
        )
        execute_query(
            "UPDATE worker_profiles SET avg_rating=%s, total_jobs=%s WHERE worker_id=%s",
            (avg_data[0]['avg_s'], avg_data[0]['total'], worker_id),
            commit=True
        )
        
        # Mark job and booking as completed
        execute_query("UPDATE jobs SET status='completed' WHERE job_id=%s", (job_id,), commit=True)
        execute_query("UPDATE bookings SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE booking_id=%s", (booking_id,), commit=True)
        
        flash('Review submitted and job completed!', 'success')
        
    return redirect(url_for('dashboard'))
