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
    def __init__(self, user_id, full_name, role):
        self.id = user_id
        self.full_name = full_name
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    result = execute_query("SELECT user_id, full_name, role FROM users WHERE user_id = %s", (user_id,))
    if result:
        return User(result[0]['user_id'], result[0]['full_name'], result[0]['role'])
    return None

@app.route('/')
def index():
    return render_template('index.html')
