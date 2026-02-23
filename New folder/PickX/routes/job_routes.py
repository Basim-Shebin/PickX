from flask import Blueprint, render_template, request, session, redirect
from extensions import mysql

job_bp = Blueprint("job", __name__)

@job_bp.route("/customer/job/create", methods=["GET", "POST"])
def create_job():

    # Only logged-in users
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        skill_required = request.form["skill_required"]
        description = request.form["description"]
        location = request.form["location"]
        customer_id = session["user_id"]

        cursor = mysql.connection.cursor()
        cursor.execute(
            """
            INSERT INTO jobs(customer_id, skill_required, description, location)
            VALUES (%s, %s, %s, %s)
            """,
            (customer_id, skill_required, description, location),
        )
        mysql.connection.commit()

        return "Job posted successfully"

    return render_template("customer/create_job.html")