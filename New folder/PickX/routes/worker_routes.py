from flask import Blueprint, render_template, request, session, redirect
from extensions import mysql
import MySQLdb.cursors

worker_bp = Blueprint("worker", __name__)

# =========================
# WORKER PROFILE (CREATE/UPDATE)
# =========================
@worker_bp.route("/worker/profile", methods=["GET", "POST"])
def worker_profile():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # SAVE / UPDATE PROFILE
    if request.method == "POST":
        skill = request.form["skill"]
        price = request.form["price"]
        availability = request.form["availability"]

        # Check if profile exists
        cursor.execute(
            "SELECT worker_id FROM workers WHERE user_id=%s",
            (user_id,)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE workers
                SET skill=%s, price=%s, availability=%s
                WHERE user_id=%s
                """,
                (skill, price, availability, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO workers(user_id, skill, price, availability)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, skill, price, availability),
            )

        mysql.connection.commit()

    # LOAD PROFILE
    cursor.execute(
        "SELECT * FROM workers WHERE user_id=%s",
        (user_id,)
    )
    profile = cursor.fetchone()

    return render_template("worker/profile.html", profile=profile)


# =========================
# VIEW MATCHING JOBS
# =========================
@worker_bp.route("/worker/jobs")
def worker_jobs():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get worker skill
    cursor.execute(
        "SELECT skill FROM workers WHERE user_id=%s",
        (user_id,)
    )
    worker = cursor.fetchone()

    if not worker:
        return "Create worker profile first"

    skill = worker["skill"]

    # Get matching jobs
    cursor.execute(
        "SELECT * FROM jobs WHERE skill_required=%s",
        (skill,)
    )
    jobs = cursor.fetchall()

    return render_template("worker/jobs.html", jobs=jobs, skill=skill)