from flask import Flask, redirect, url_for, render_template, request, session, flash, jsonify
from db_connection import get_connection
import pymysql
from datetime import datetime
import re
from datetime import datetime


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
        print(role,username,password)

        if connection:
            try:
                with connection.cursor() as my_cursor:
                    my_cursor.execute(
                        "SELECT * FROM login_cred WHERE Username = %s AND Password = %s",
                        (username, password)
                    )
                    result = my_cursor.fetchone()
                    print(result)

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

        if title and description:
            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO announcements (title, description, date_posted) VALUES (%s, %s,CURDATE())"
                    cursor.execute(sql, (title, description))
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
        print('Unauthoriszed acess')
        return redirect(url_for('login'))

    if request.method == "POST":
        complaint_id = request.form.get("complaint_id")
        staff_name = request.form.get("staff_name")

        if not complaint_id or not staff_name:
            print("Error: Complaint ID or Staff Name is missing")
            return jsonify(success=False, error="Complaint ID or Staff Name is missing"), 400

        try:
            with connection.cursor() as cursor:
                # Update the assigned_staff column in the complaint table
                sql_update = """
                UPDATE complaint 
                SET assigned_staff = %s 
                WHERE c_id = %s
                """
                cursor.execute(sql_update, (staff_name, complaint_id))
                connection.commit()
            return jsonify(success=True)  # Return JSON response indicating success
        except Exception as e:
            print(f"Error updating complaint: {str(e)}")
            return jsonify(success=False, error=str(e)), 500  # Return JSON response indicating failure

    # GET request: Fetch complaints and staff data
    try:
        with connection.cursor() as cursor:
            sql_complaints = """
            SELECT 
                c.c_id as complaint_id,
                s.Name AS student_name,
                c.R_NO AS room_no,
                c.Description AS description,
                c.Category AS Category,
                c.Date_OF_SUBMISSION AS date_submitted,
                c.Status AS status,
                c.assigned_staff AS assigned_staff
            FROM 
                complaint c
            JOIN 
                student s ON c.SRN = s.SRN
            WHERE 
                s.Unit = %s AND c.Status IN ('Pending', 'Assigned')
            """
            user_unit = session['Unit']
            cursor.execute(sql_complaints, user_unit)
            complaints = cursor.fetchall()

            # Fetch staff by category
            category_to_role = {
                'Electrical': 'Electrician',
                'Furniture': 'Carpenter',
                'Plumbing': 'Plumber'
            }
            staff_by_category = {}
            for category, role in category_to_role.items():
                sql_staff = "SELECT Fname FROM maintenancestaff WHERE work=%s"
                cursor.execute(sql_staff, (role,))
                staff_by_category[category] = cursor.fetchall()

    except Exception as e:
        flash(f"Error fetching complaints or staff: {str(e)}", "error")

    return render_template("admin/complaints.html", 
                           complaints=complaints, 
                           staff_by_category=staff_by_category, 
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
                """, (fname+" "+lname,m_id, m_id, "NULL"))  # Password is the same as the M_ID

                flash("Maintenance staff created successfully!", "success")
        
            # Commit the transaction
            connection.commit()


        except pymysql.MySQLError as e:
            # Handle any database errors
            flash(f"An error occurred: {e}", "alert")
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

#---------------------X------------------------X-----------------------------------------

@app.route("/student")
def student_dashboard():
    if 'Username' not in session or session['Role'] != 'Student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    username = session['Username']  # Assuming you store the username in session
    student_srn = username.upper()  # Assuming the username is in the format S_<SRN>

    cursor = connection.cursor()

    # Fetch student details using the SRN
    query_student = "SELECT * FROM student WHERE SRN = %s"
    cursor.execute(query_student, (student_srn,))
    student_details = cursor.fetchone()

    if not student_details:
        flash('Student details not found', 'error')
        cursor.close()
        return redirect(url_for('login'))

    # Fetch room details using the Room_No from student details
    room_no = student_details['Room_no']
    query_room = "SELECT * FROM room WHERE R_No = %s"
    cursor.execute(query_room, (room_no,))
    room_details = cursor.fetchone()

    # Fetch warden details based on the unit of the student
    query_warden = "SELECT * FROM warden WHERE unit = %s"
    cursor.execute(query_warden, (student_details['Unit'],))
    warden_details = cursor.fetchone()

    # Call the MySQL function to fetch the menu for today
    cursor.execute("SELECT GetMenuForToday()")
    menu_result = cursor.fetchone()

    # Debugging: Check the menu result
    print("Menu Result:", menu_result)

    # Extract the menu string and parse it using regex
    if menu_result and 'GetMenuForToday()' in menu_result:
        menu_string = menu_result['GetMenuForToday()']  # Correctly access the value

        # Use regular expression to capture each menu item
        menu_regex = r"Breakfast: (.*?), Lunch: (.*?), Snacks: (.*?), Dinner: (.*)"
        match = re.search(menu_regex, menu_string)

        if match:
            breakfast = match.group(1)
            lunch = match.group(2)
            snacks = match.group(3)
            dinner = match.group(4)
        else:
            # If regex doesn't match, set default values
            breakfast = lunch = snacks = dinner = "No Menu Available"

        # Debugging: Check the extracted menu items
        print(f"Breakfast: {breakfast}, Lunch: {lunch}, Snacks: {snacks}, Dinner: {dinner}")

        # Create the menu dictionary to pass to the template
        menu_item = {
            'day': datetime.now().strftime('%A'),  # Get the current day
            'breakfast': breakfast,
            'lunch': lunch,
            'snacks': snacks,
            'dinner': dinner
        }
    else:
        # Fallback if menu_result is empty
        menu_item = {
            'day': datetime.now().strftime('%A'),
            'breakfast': 'No Menu Available',
            'lunch': 'No Menu Available',
            'snacks': 'No Menu Available',
            'dinner': 'No Menu Available'
        }

    # Fetch the latest announcements from the announcements table
    query_announcements = "SELECT title, description, date_posted FROM announcements ORDER BY date_posted DESC"
    cursor.execute(query_announcements)
    announcements = cursor.fetchall()

    # Fetch roommates based on Room_No and Unit, excluding the current student
    query_roommates = """
        SELECT Name, SRN, Branch, Year, Phone_no FROM student 
        WHERE Room_No = %s AND SRN != %s AND Unit = %s
    """
    cursor.execute(query_roommates, (room_no, student_srn, student_details['Unit']))
    roommates = cursor.fetchall()

    cursor.close()

    return render_template("student.html", 
                           menu=menu_item, 
                           announcements=announcements, 
                           username=session.get('FName'),
                           student=student_details, 
                           room=room_details, 
                           warden=warden_details, 
                           roommates=roommates)



@app.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    if 'Username' not in session or session['Role'] != 'Student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    category = request.form['Category']
    description = request.form['Description']
    username = session['Username'] # Assuming you store the username in session
    cursor = connection.cursor()

    # Fetch student details using the Username from session
    query_student = "SELECT SRN, Room_No,Unit  FROM student WHERE SRN = %s"
    cursor.execute(query_student, (username,))
    student = cursor.fetchone()

    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('student_complaint'))

    srn = student['SRN']
    room_no = student['Room_No']
    unit_no=student['Unit']
    status = "Pending"

    # Insert the complaint into the database
    query = """
    INSERT INTO complaint (R_NO, SRN, Category, Description, Date_OF_SUBMISSION, Status, Unit_No)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (room_no, srn, category, description, datetime.now(), status, unit_no))
    connection.commit()  # Commit the transaction

    cursor.close()

    # Redirect to the complaints page after submission
    return redirect(url_for('student_complaint'))  # Ensure this matches the route for complaints

@app.route('/student/complaint')
def student_complaint():
    if 'Username' not in session or session['Role'] != 'Student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    username = session['Username']
    print(f"Logged-in username: {username}")  # Debugging line to check username type and value

    # Fetch student details
    cursor = connection.cursor()  # Use dictionary cursor for easy access to columns
    query_student = "SELECT SRN, Name FROM student WHERE SRN = %s"
    cursor.execute(query_student, (username,))
    student = cursor.fetchone()
    print(student)  # Debugging line to check student data
    cursor.close()  # Close the cursor after fetching the student data

    # Check if student exists
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('login'))

    # Fetch complaints for the logged-in student using their SRN
    cursor = connection.cursor()  # Use a new cursor for fetching complaints
    query_complaints = """
    SELECT C_ID, R_NO, Category, Description, Date_OF_SUBMISSION, Status
    FROM complaint
    WHERE SRN = %s
    """
    cursor.execute(query_complaints, (username,))
    complaints = cursor.fetchall()
    cursor.close()  # Close the cursor after fetching complaints

    # Check if there are any complaints
    message = "You have not filed any complaints yet." if not complaints else None

    # Render template with student and complaints data
    return render_template(
        'complaint.html', 
        complaints=complaints, 
        message=message, 
        username=username,
        student=student
    )

@app.route('/student/update-password', methods=['GET', 'POST'])
def student_update_password():
    if 'Username' not in session or session['Role'] != 'Student':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    username = session['Username']

    if request.method == 'POST':
        current_password = request.form['currentPassword']
        new_password = request.form['newPassword']
        confirm_password = request.form['confirmPassword']

        print(current_password)
        print(new_password)
        print(confirm_password)

        # Check if passwords match
        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('student_update_password'))

        # Check if the new password is the same as the current password
        if new_password == current_password:
            flash("New password cannot be the same as the current password.", "error")
            return redirect(url_for('student_update_password'))

        try:
            # Check if the current password is correct
            cursor = connection.cursor()
            query_check_password = "SELECT Password FROM login_cred WHERE Username = %s"
            cursor.execute(query_check_password, (username,))
            result = cursor.fetchone()

            if result is None:
                flash("Username not found.", "error")
                return redirect(url_for('student_update_password'))

            if result['Password'] != current_password:
                flash("Current password is incorrect.", "error")
                return redirect(url_for('student_update_password'))

            # Update the password in the database
            query_update_password = "UPDATE login_cred SET Password = %s WHERE Username = %s"
            cursor.execute(query_update_password, (new_password, username))
            connection.commit()

            flash("Password updated successfully", "success")
            return redirect(url_for('student_dashboard'))

        except Exception as e:
            connection.rollback()  # Rollback in case of error
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('student_update_password'))

        finally:
            cursor.close()

    # If it's a GET request, render the password update page
    cursor = connection.cursor()
    query_student = "SELECT SRN, Name FROM student WHERE SRN = %s"
    cursor.execute(query_student, (username,))
    student = cursor.fetchone()
    cursor.close()

    return render_template('update_password.html', student=student)




@app.route('/maintenance')
def maintenance_dashboard():
    if 'Username' not in session or session['Role'] != 'Maintenance':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    # Get the maintenance staff's ID or work from the session
    maintenance_id = session['Username']  # Assuming Username is used to identify the staff
    cursor = connection.cursor()

    # Mapping between Work values in maintenancestaff and complaint categories
    work_category_map = {
        'Carpenter': 'Furniture',     # Carpenter maps to 'Furniture'
        'Plumber': 'Plumbing',      # Plumber maps to 'Plumbing'
        'Electrician': 'Electrical'     # Electrician maps to 'Electrical'
    }

    # Get the work category for the maintenance staff
    cursor.execute("SELECT Work,Fname FROM maintenancestaff WHERE M_ID = %s", (maintenance_id,))
    maintenance_work_record = cursor.fetchone()
    cursor.close()

    if maintenance_work_record:
        work_code = maintenance_work_record['Work']
        fname=maintenance_work_record['Fname']
        category = work_category_map.get(work_code)  # Get the complaint category

        # If a valid category is found, fetch matching complaints
        if category:
            cursor = connection.cursor()
            query = """
            SELECT C_ID, R_NO, Category, Description, Date_OF_SUBMISSION, Status 
            FROM complaint 
            WHERE Category = %s AND assigned_staff=%s
            """
            cursor.execute(query, (category,fname))
            complaints = cursor.fetchall()
            cursor.close()
            
            return render_template("maintenance.html", complaints=complaints, username=session.get('FName'))
        else:
            flash("Invalid work category for maintenance staff.", "error")
            return redirect(url_for('login'))
    else:
        flash("Maintenance staff not found.", "error")
        return redirect(url_for('login'))

@app.route('/update_complaint_status/<int:c_id>', methods=['POST'])
def update_complaint_status(c_id):
    if 'Username' not in session or session['Role'] != 'Maintenance':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    cursor = connection.cursor()

    # Check the current status of the complaint
    cursor.execute('SELECT Status FROM complaint WHERE C_ID = %s', (c_id,))
    result = cursor.fetchone()

    # Update the status if it is pending
    if result and result['Status'] == 'Pending':
        cursor.execute('UPDATE complaint SET Status = %s WHERE C_ID = %s', ('Resolved', c_id))
        connection.commit()
        flash('Complaint status updated to Resolved', 'success')
    else:
        flash('Complaint not found or already resolved', 'warning')

    cursor.close()
    
    # Redirect back to the maintenance page to refresh the data
    return redirect(url_for('maintenance_dashboard'))

@app.route("/security")
def security_dashboard():
    if 'Username' not in session or session['Role'] != 'Security':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    cursor = connection.cursor()
    
    # Fetch the security staff's unit based on their username from the session
    cursor.execute("SELECT Unit FROM security WHERE S_ID = %s", (session['Username'],))
    security_unit = cursor.fetchone()
    print(security_unit)

    # Ensure the security unit exists in session data before proceeding
    if not security_unit:
        flash("Unable to fetch security unit information.", "error")
        return redirect(url_for('login'))

    # Extract the unit from the result
    unit_no = security_unit['Unit']  # Assuming fetchone() returns a tuple
    print(unit_no)
    # Fetch currently visiting visitors (exit time is NULL) for the same unit
    cursor.execute("""
        SELECT logs.log_ID, visitor.visitor_name, visitor.contact_no, visitor.Relation, 
               student.Name AS visiting_student_name, student.Room_No, logs.entry_time 
        FROM logs 
        JOIN visitor ON logs.Visitor_ID = visitor.visitor_ID 
        JOIN student ON logs.student_SRN = student.SRN 
        WHERE logs.exit_time IS NULL AND logs.unit_no = %s
    """, (unit_no,))
    current_visitors = cursor.fetchall()
    print(current_visitors)
    
    # Fetch visitor history (where exit time is NOT NULL) for the same unit
    cursor.execute("""
        SELECT logs.log_ID, visitor.visitor_name, visitor.contact_no, visitor.Relation, 
               student.Name AS visiting_student_name, student.Room_No, logs.entry_time, logs.exit_time
        FROM logs 
        JOIN visitor ON logs.Visitor_ID = visitor.visitor_ID 
        JOIN student ON logs.student_SRN = student.SRN 
        WHERE logs.exit_time IS NOT NULL AND logs.unit_no = %s
    """, (unit_no,))
    visitor_history = cursor.fetchall()
    print(visitor_history)
    cursor.close()

    return render_template("security.html", current_visitors=current_visitors, visitor_history=visitor_history, username=session.get('FName'))



@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    if 'Username' not in session or session['Role'] != 'Security':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    srn = request.form['visiting_SRN']
    visitor_name = request.form['visitor_name']
    gender = request.form['gender']
    contact_no = request.form['contact_no']
    email = request.form['email']
    city = request.form['city']
    state = request.form['state']
    relation = request.form['relation']
    
    cursor = connection.cursor()

    # Get the unit of the security staff from the session
    cursor.execute("SELECT Unit FROM security WHERE S_ID = %s", (session['Username'],))
    security_unit_record = cursor.fetchone()

    if security_unit_record:
        unit_no = security_unit_record['Unit']
    else:
        cursor.close()
        flash("Unable to fetch security unit information.", "error")
        return redirect(url_for('security_dashboard'))

    # Get the unit of the student to verify it matches the security unit
    cursor.execute("SELECT Unit FROM student WHERE SRN = %s", (srn,))
    student_unit_record = cursor.fetchone()

    if not student_unit_record or student_unit_record['Unit'] != unit_no:
        cursor.close()
        flash("The student is not from your unit. Cannot add visitor.", "error")
        return redirect(url_for('security_dashboard'))

    # Insert visitor record
    cursor.execute("""
        INSERT INTO visitor (visitor_name, gender, contact_no, email, city, state, visiting_SRN, Relation, unit_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (visitor_name, gender, contact_no, email, city, state, srn, relation, unit_no))
    visitor_id = cursor.lastrowid

    # Insert log record with entry time as current time, exit time as NULL, and unit as security's unit
    cursor.execute("""
        INSERT INTO logs (Visitor_ID, student_SRN, entry_time, unit_no)
        VALUES (%s, %s, %s, %s)
    """, (visitor_id, srn, datetime.now(), unit_no))
    
    connection.commit()
    cursor.close()

    flash("Visitor added successfully.", "success")
    return redirect(url_for('security_dashboard'))


@app.route('/record_exit/<int:log_id>', methods=['POST'])
def record_exit(log_id):
    if 'Username' not in session or session['Role'] != 'Security':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    cursor = connection.cursor()

    # Get the unit of the security staff from the session
    cursor.execute("SELECT Unit FROM security WHERE S_ID = %s", (session['Username'],))
    security_unit_record = cursor.fetchone()

    # Ensure security unit exists in session data before proceeding
    if security_unit_record:
        unit_no = security_unit_record['Unit']
    else:
        cursor.close()
        flash("Unable to fetch security unit information.", "error")
        return redirect(url_for('security_dashboard'))

    # Check if the log entry belongs to the same unit as the security staff
    cursor.execute("""
        SELECT log_ID FROM logs WHERE log_ID = %s AND unit_no = %s AND exit_time IS NULL
    """, (log_id, unit_no))
    log_entry = cursor.fetchone()

    # Update exit time if the log entry exists and belongs to the correct unit
    if log_entry:
        cursor.execute("""
            UPDATE logs SET exit_time = %s WHERE log_ID = %s
        """, (datetime.now(), log_id))
        connection.commit()
        flash("Exit recorded successfully.", "success")
    else:
        flash("Log entry not found or already recorded.", "error")

    cursor.close()

    return redirect(url_for('security_dashboard'))


# Logout route
@app.route("/logout")
def logout():
    if 'Username' in session:
        session.clear()
        flash("Successfully logged out", "success")
    return redirect(url_for('landing'))

if __name__ == "__main__":
    app.run(debug=True)