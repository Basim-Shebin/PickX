import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, SECRET_KEY
from extensions import mysql

# =========================
# CREATE FLASK APP
# =========================
app = Flask(__name__)
app.secret_key = SECRET_KEY

# =========================
# DATABASE CONFIG
# =========================
app.config["MYSQL_HOST"] = MYSQL_HOST
app.config["MYSQL_USER"] = MYSQL_USER
app.config["MYSQL_PASSWORD"] = MYSQL_PASSWORD
app.config["MYSQL_DB"] = MYSQL_DB

# Initialize MySQL with Flask
mysql.init_app(app)

# =========================
# REGISTER BLUEPRINTS
# =========================
from routes.auth_routes import auth_bp
from routes.worker_routes import worker_bp
from routes.job_routes import job_bp

app.register_blueprint(auth_bp)
app.register_blueprint(worker_bp)
app.register_blueprint(job_bp)

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    print("Starting PickX Flask App...")
    app.run(debug=True)