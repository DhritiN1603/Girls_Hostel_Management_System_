from flask import Flask, redirect, url_for, render_template, request, session, flash,jsonify
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
                flash(f"Login error: {str(e)}")
                flash("An error occurred during login", "error")
            finally:
                my_cursor.close()
        else:
            print("Database connection failed", "error")
    
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
            print("Failed to connect to the database", "error")

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
            unit = session.get('Unit')
            sql_students = "SELECT COUNT(*) FROM student WHERE unit = %s"
            cursor.execute(sql_students, (unit,))
            total_students = cursor.fetchone()['COUNT(*)'] 
            
            sql_complaints = "SELECT COUNT(*) FROM complaint WHERE status = 'Pending' AND Unit_No = %s"
            cursor.execute(sql_complaints, (unit,))
            active_complaints = cursor.fetchone()['COUNT(*)']
            
            sql_count= "SELECT COUNT(*) FROM announcements"
            cursor.execute(sql_count)
            announcement_count= cursor.fetchone()['COUNT(*)']
            
            sql = "SELECT title, description, date_posted FROM announcements ORDER BY date_posted DESC LIMIT 5"
            cursor.execute(sql)
            announcements = cursor.fetchall()
            query = """SELECT Unit,COUNT(CASE WHEN Capacity > Occupied THEN 1 END) AS Available_Rooms FROM room where Unit=%s;"""
            cursor.execute(query,(unit,))
            available_rooms=cursor.fetchone()['Available_Rooms']
            
    except Exception as e:
        flash(f"Error fetching announcements: {str(e)}", "error")
        announcements = []
        total_students = 0
        active_complaints = 0
        announcement_count = 0
        available_rooms = 0
    
    return render_template("admin/admin_home.html", 
                           announcements=announcements, total_students=total_students,
                            active_complaints=active_complaints,announcement=announcement_count,
                            available_rooms=available_rooms,
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
            sql = "SELECT fname, srn, year, unit FROM registered where unit=%s"
            user_unit=session.get('Unit')
            cursor.execute(sql,user_unit)
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
    
    complaints = []
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                s.Name AS student_name,
                c.R_NO AS room_no,
                c.Description AS description,
                c.Date_OF_SUBMISSION AS date_submitted,
                c.Status AS status 
            FROM 
                complaint c
            JOIN 
                student s ON c.SRN = s.SRN
            WHERE 
                s.Unit = %s
            """
            user_unit=session['Unit']
            cursor.execute(sql,user_unit)
            complaints = cursor.fetchall()

    except Exception as e:
        flash(f"Error fetching complaints: {str(e)}", "error")

    return render_template("admin/complaints.html", 
                           complaints=complaints, 
                           username=session.get('FName'))


@app.route("/admin/create_user", methods=["POST", "GET"])
def create_user():

    if 'Username' not in session or session['Role'] != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    unit = session.get('Unit')
    room_list = []
    try:
        with connection.cursor() as cursor:
            sql_room = "SELECT R_no FROM room WHERE unit=%s"
            cursor.execute(sql_room, (unit,))
            rooms = cursor.fetchall()
            room_list = [room['R_no'] for room in rooms]
    except Exception as e:
        flash(f"Error fetching rooms: {str(e)}")
    if request.method == "POST":
        role = request.form.get('role')
        try:
            cursor = connection.cursor()
            
            if role == 'Student':
                
                # Insert into the student table
                
                full_name = request.form['name']
                srn = request.form['srn']
                email = request.form['email']
                phone_no = request.form['phone_no']
                dob = request.form['dob']
                branch = request.form['branch']
                year = request.form['year']
                room = request.form['room']
                address = request.form['address']

                cursor.execute("""
                    INSERT INTO student (Name, SRN, Email, Phone_no, DOB, Unit, Branch, Year, Room_No, Address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (full_name, srn, email, phone_no, dob, unit, branch, year, room, address))
                flash("Student created successfully!", "success")

            elif role == 'Security':
                # Insert into the security table, using S_ID as username and password
                s_id = request.form['sid']
                fname = request.form['fname']
                lname = request.form['lname']
                phone_no = request.form['phone']
                shift = request.form['shift']

                # Insert into security table
                cursor.execute("""
                    INSERT INTO security (S_ID, Fname, Lname, Phone_no, Unit, shift)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (s_id, fname, lname, phone_no, unit, shift))

                # Insert into login_cred table with username and password as S_ID
                cursor.execute("""
                    INSERT INTO login_cred (Fname,Username, Password, Role, Unit)
                    VALUES (%s,%s, %s, 'Security', %s)
                """, (fname+" "+lname,s_id, s_id, unit))  # Password is the same as the S_ID

                flash("Security staff created successfully!", "success")

            elif role == 'Maintenance':
                # Insert into the maintenance staff table, using M_ID as username and password
                m_id = request.form['mid']
                fname = request.form['fname_m']
                lname = request.form['lname_m']
                contact = request.form['phone_m']
                work = request.form['job']

                # Insert into maintenancestaff table
                cursor.execute("""
                    INSERT INTO maintenancestaff (M_ID, Fname, Lname, Contact, Work)
                    VALUES (%s, %s, %s, %s, %s)
                """, (m_id, fname, lname, contact, work))

                # Insert into login_cred table with username and password as M_ID
                cursor.execute("""
                    INSERT INTO login_cred (Fname ,Username, Password, Role, Unit)
                    VALUES (%s,%s, %s, 'Maintenance', %s)
                """, (fname+" "+lname,m_id, m_id, unit))  # Password is the same as the M_ID

                flash("Maintenance staff created successfully!", "success")
        
            # Commit the transaction
            connection.commit()


        except pymysql.MySQLError as e:
            # Handle any database errors
            flash(f"An error occurred: {e}", "error")
            connection.rollback()

        finally:
            cursor.close()

        return redirect(url_for('create_user'))

    # Render the form page
    return render_template("admin/create_user.html",room_list=room_list, username=session.get('FName'))

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

@app.route('/edit_menu/<day>', methods=['POST'])
def edit_menu(day):
    breakfast = request.form['breakfast']
    lunch = request.form['lunch']
    snacks = request.form['snacks']
    dinner = request.form['dinner']

    with connection.cursor() as cursor:
        update_query = """
        UPDATE menu
        SET breakfast = %s, lunch = %s, snacks = %s, dinner = %s
        WHERE day = %s;
        """
        try:
            cursor.execute(update_query, (breakfast, lunch, snacks, dinner, day))
            connection.commit()
            return jsonify(success=True)
        except Exception as e:
            connection.rollback()
            ("Error updating menu:", e)
            return jsonify(success=False)


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


#---- common logout for all users-----------
# Logout route
@app.route("/logout")
def logout():
    if 'Username' in session:
        session.clear()
        flash("Successfully logged out", "success")
    return redirect(url_for('landing'))

if __name__ == "__main__":
    app.run(debug=True)