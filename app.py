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
            all_open_jobs = execute_query(
                "SELECT * FROM jobs WHERE status = 'open' AND (title LIKE %s OR skill_required LIKE %s OR location_city LIKE %s OR location_area LIKE %s)",
                (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')
            )
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
        
        return render_template('worker_dashboard.html', profile=profile, recommended_jobs=recommended_jobs, search_query=search_query)
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

        # Handle Portfolio Images
        portfolio_files = request.files.getlist('portfolio_images')
        for p_file in portfolio_files:
            p_path = save_upload(p_file, 'portfolios')
            if p_path:
                execute_query("INSERT INTO worker_portfolio (worker_id, image_path) VALUES (%s, %s)", (current_user.id, p_path), commit=True)

        execute_query(
            "UPDATE worker_profiles SET bio=%s, daily_wage=%s, experience_years=%s, availability_status=%s, skills=%s WHERE worker_id=%s",
            (bio, daily_wage, experience_years, availability_status, skills, current_user.id),
            commit=True
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('worker_profile'))

    profile = execute_query("SELECT * FROM worker_profiles WHERE worker_id = %s", (current_user.id,))
    return render_template('worker_profile.html', profile=profile[0] if profile else None, categories=JOB_CATEGORIES)

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
