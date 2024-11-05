from flask import Flask, redirect, url_for, render_template, request, session, flash
from sql_connector import get_connection
import pymysql

app = Flask(__name__)
app.secret_key = "dbms_ghms"
connection = get_connection()
session_cleared = False

@app.before_request
def clear_session_once():
    global session_cleared
    if not session_cleared:
        session.clear()
        session_cleared = True

# Landing page route
@app.route("/", methods=["POST", "GET"])
def landing():
    return render_template("landing.html")

# Login route with session management
@app.route("/login", methods=["POST", "GET"])
def login():
    if 'Username' in session:
        if session['Role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif session['Role'] == 'Student':
            return redirect(url_for('student_dashboard'))
        elif session['Role'] == 'Security':
            return redirect(url_for('security_dashboard'))
        elif session['Role'] == 'Maintenance':
            return redirect(url_for('maintenance_dashboard'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if connection:
            try:
                with connection.cursor() as my_cursor:
                    my_cursor.execute(
                        "SELECT * FROM login_cred WHERE Username = %s AND Password = %s",
                        (username, password)
                    )
                    result = my_cursor.fetchone()

                    if result:
                        selected_role = None
                        if role == '1' and result['Role'] == 'Admin':
                            selected_role = 'Admin'
                        elif role == '2' and result['Role'] == 'Student':
                            selected_role = 'Student'
                        elif role == '3' and result['Role'] == 'Security':
                            selected_role = 'Security'
                        elif role == '4' and result['Role'] == 'Maintenance':
                            selected_role = 'Maintenance'

                        if selected_role:
                            session['Username'] = result['Username']
                            session['Role'] = result['Role']
                            session['FName'] = result['FName']
                            session['Unit'] = result['Unit']

                            if selected_role == 'Admin':
                                return redirect(url_for('admin_dashboard'))
                            elif selected_role == 'Student':
                                return redirect(url_for('student_dashboard'))
                            elif selected_role == 'Security':
                                return redirect(url_for('security_dashboard'))
                            elif selected_role == 'Maintenance':
                                return redirect(url_for('maintenance_dashboard'))
                        else:
                            flash("Invalid role selected for this user", "error")
                    else:
                        flash("Invalid username or password", "error")

            except Exception as e:
                print(f"Login error: {str(e)}")
                flash("An error occurred during login", "error")
            finally:
                my_cursor.close()
        else:
            flash("Database connection failed", "error")
    
    return render_template("login.html")

# Signup route
@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        full_name = request.form.get("fname")
        srn = request.form.get("srn")
        year = request.form.get("year")
        unit = request.form.get("unit")

        if connection:
            try:
                with connection.cursor() as my_cursor:
                    sql_query = """
                    INSERT INTO registered (fname, srn, year, unit) 
                    VALUES (%s, %s, %s, %s)
                    """
                    my_cursor.execute(sql_query, (full_name, srn, year, unit))
                    connection.commit()
                    flash("Registration successful. You can now log in once room alloted.", "success")
                    return redirect(url_for('login'))
            except Exception as e:
                flash(f"An error occurred during signup: {str(e)}", "error")
            finally:
                my_cursor.close()
        else:
            flash("Failed to connect to the database", "error")

    return render_template("signup.html")

# Admin Routes
@app.route("/admin/home", methods=["POST", "GET"])
def admin_dashboard():
    if 'Username' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    if session['Role'] != 'Admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('login'))
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT title, description, date_posted FROM announcements ORDER BY date_posted DESC LIMIT 5"
            cursor.execute(sql)
            announcements = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching announcements: {str(e)}", "error")
        announcements = []
    
    return render_template("admin/admin_home.html", 
                         announcements=announcements, 
                         username=session.get('FName'))

@app.route("/admin/announcements", methods=["POST", "GET"])
def announcements():
    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        date_posted = request.form.get("date")

        if title and description and date_posted:
            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO announcements (title, description, date_posted) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (title, description, date_posted))
                    connection.commit()
                    flash("Announcement added successfully!", "success")
            except Exception as e:
                flash(f"Error: {str(e)}", "error")

    return render_template("admin/announcements.html", username=session.get('FName'))

@app.route("/admin/registered", methods=["POST", "GET"])
def registered_students():
    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    registered_students = []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT fname, srn, year, unit FROM registered"
            cursor.execute(sql)
            registered_students = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching registered students: {str(e)}", "error")

    return render_template("admin/registered.html", 
                           registered_students=registered_students, 
                           username=session.get('FName'))

@app.route("/admin/complaints", methods=["POST", "GET"])
def complaints():
    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template("admin/complaints.html", username=session.get('FName'))

@app.route("/admin/create_user", methods=["POST", "GET"])
def create_user():
    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template("admin/create_user.html", username=session.get('FName'))

@app.route("/admin/menu", methods=["POST", "GET"])
def menu():
    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    try:
        with connection.cursor() as cursor:
            sql = "SELECT day, breakfast, lunch, snacks, dinner FROM menu ORDER By id"
            cursor.execute(sql)
            menu_items = cursor.fetchall()
            return render_template('admin/menu.html', 
                                menu_items=menu_items, 
                                username=session.get('FName'))
    except pymysql.Error as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

# Student dashboard (add your student routes here)
@app.route("/student/dashboard")
def student_dashboard():
    if 'Username' not in session or session['Role'] != 'Student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template("student/dashboard.html", username=session.get('FName'))

# Security dashboard (add your security routes here)
@app.route("/security/dashboard")
def security_dashboard():
    if 'Username' not in session or session['Role'] != 'Security':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template("security/dashboard.html", username=session.get('FName'))

# Maintenance dashboard (add your maintenance routes here)
@app.route("/maintenance/dashboard")
def maintenance_dashboard():
    if 'Username' not in session or session['Role'] != 'Maintenance':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    return render_template("maintenance/dashboard.html", username=session.get('FName'))

# Logout route
@app.route("/logout")
def logout():
    if 'Username' in session:
        session.clear()
        flash("Successfully logged out", "success")
    return redirect(url_for('landing'))

if __name__ == "__main__":
    app.run(debug=True)