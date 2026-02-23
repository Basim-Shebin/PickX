from flask import Blueprint, render_template, request, redirect, session
from extensions import mysql
import MySQLdb.cursors

auth_bp = Blueprint("auth", __name__)

# LOGIN PAGE
@auth_bp.route("/")
def login_page():
    return render_template("common/login.html")

# REGISTER
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,%s)",
            (name, email, password, role),
        )
        mysql.connection.commit()

        return redirect("/")

    return render_template("common/register.html")

# LOGIN
@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password),
    )
    user = cursor.fetchone()

    if user:
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        return redirect("/worker/profile")
    else:
        return "Invalid login"