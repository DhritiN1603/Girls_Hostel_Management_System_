from flask import Flask, render_template, request, jsonify, redirect, url_for
from db_connection import get_connection
from datetime import datetime  # Import datetime module

app = Flask(__name__)

# Home route (optional)
@app.route('/')
def home():
    return "Hello"  # Create an index.html if needed

@app.route('/student')
def student():
    # Get the current day of the week
    current_day = datetime.now().strftime('%A')  # e.g., 'Monday'
    
    # Connect to the database
    connection = get_connection()
    cursor = connection.cursor()
    
    # Fetch the menu for the current day
    query_menu = "SELECT * FROM menu WHERE day = %s"
    cursor.execute(query_menu, (current_day,))
    result = cursor.fetchone()  # Fetch a single record for the menu
    
    # Check if a menu is available for the current day and create a dictionary
    if result:
        menu_item = {
            'id': result['id'],
            'day': result['day'],
            'breakfast': result['breakfast'],
            'lunch': result['lunch'],
            'snacks': result['snacks'],
            'dinner': result['dinner']
        }
    else:
        # Handle the case where no menu is found for the current day
        menu_item = {
            'day': current_day,
            'breakfast': 'No Menu Available',
            'lunch': 'No Menu Available',
            'snacks': 'No Menu Available',
            'dinner': 'No Menu Available'
        }

    # Fetch the latest announcements from the announcements table
    query_announcements = "SELECT title, description, date_posted FROM announcements ORDER BY date_posted DESC"
    cursor.execute(query_announcements)
    announcements = cursor.fetchall()
    
    cursor.close()
    connection.close()

    # Pass both the menu and announcements data to the template
    return render_template('student.html', menu=menu_item, announcements=announcements)

@app.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    category = request.form['Category']
    description = request.form['Description']
    unit_no = request.form['Unit_No']
    room_no = "R001"  # This should be dynamically fetched based on the logged-in user if applicable
    srn = "SRN001"    # This should also be dynamically fetched if applicable
    status = "Pending"

    connection = get_connection()
    cursor = connection.cursor()

    # Insert the complaint into the database
    query = """
    INSERT INTO complaint (R_NO, SRN, Category, Description, Date_OF_SUBMISSION, Status, Unit_No)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (room_no, srn, category, description, datetime.now(), status, unit_no))
    connection.commit()  # Commit the transaction

    cursor.close()
    connection.close()

    # Redirect to the complaints page after submission
    return redirect(url_for('student/complaint')) 

# Route for Student complaint page
@app.route('/student/complaint')
def student_complaint():
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute('SELECT C_ID, R_NO, Category, Description, Date_OF_SUBMISSION, Status FROM complaint')
    complaints = cursor.fetchall()
    
    cursor.close()
    connection.close()

    # Check if there are any complaints
    if not complaints:  # If the complaints list is empty
        message = "You have not filed any complaints yet."
    else:
        message = None  # No message if there are complaints
    
    return render_template('complaint.html', complaints=complaints, message=message)

    

# Route for Student update password page
@app.route('/student/update-password')
def student_update_password():
    return render_template('update_password.html')

# Route for Maintenance Staff page
@app.route('/maintenance')
def maintenance():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT C_ID, R_NO, Category, Description, Date_OF_SUBMISSION, Status FROM complaint')
    complaints = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return render_template('maintenance.html', complaints=complaints)

# Route to update complaint status
@app.route('/update_complaint_status/<int:c_id>', methods=['POST'])
def update_complaint_status(c_id):
    connection = get_connection()
    cursor = connection.cursor()

    # Check the current status of the complaint
    cursor.execute('SELECT Status FROM complaint WHERE C_ID = %s', (c_id,))
    result = cursor.fetchone()

    # Update the status if it is pending
    if result and result['Status'] == 'Pending':
        cursor.execute('UPDATE complaint SET Status = %s WHERE C_ID = %s', ('Resolved', c_id))
        connection.commit()

    cursor.close()
    connection.close()
    
    # Redirect back to the maintenance page to refresh the data
    return redirect(url_for('maintenance'))

# Route for Security page
@app.route('/security')
def security():
    connection = get_connection()
    cursor = connection.cursor()
    
    # Fetch currently visiting visitors (exit time is NULL)
    cursor.execute("""
        SELECT logs.log_ID, visitor.visitor_name, visitor.contact_no, visitor.Relation, 
               student.Name AS visiting_student_name, student.Room_No, logs.entry_time 
        FROM logs 
        JOIN visitor ON logs.Visitor_ID = visitor.visitor_ID 
        JOIN student ON logs.student_SRN = student.SRN 
        WHERE logs.exit_time IS NULL
    """)
    current_visitors = cursor.fetchall()
    
    # Fetch visitor history (where exit time is NOT NULL)
    cursor.execute("""
        SELECT logs.log_ID, visitor.visitor_name, visitor.contact_no, visitor.Relation, 
               student.Name AS visiting_student_name, student.Room_No, logs.entry_time, logs.exit_time
        FROM logs 
        JOIN visitor ON logs.Visitor_ID = visitor.visitor_ID 
        JOIN student ON logs.student_SRN = student.SRN 
        WHERE logs.exit_time IS NOT NULL
    """)
    visitor_history = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('security.html', current_visitors=current_visitors, visitor_history=visitor_history)


# Insert new visitor entry and log entry time
@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    srn = request.form['visiting_SRN']
    visitor_name = request.form['visitor_name']
    gender = request.form['gender']
    contact_no = request.form['contact_no']
    email = request.form['email']
    city = request.form['city']
    state = request.form['state']
    relation = request.form['relation']

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch the unit number of the student based on their SRN
    cursor.execute("SELECT Unit FROM student WHERE SRN = %s", (srn,))
    student_record = cursor.fetchone()

    if student_record:
        unit_no = student_record['Unit']
    else:
        cursor.close()
        conn.close()
        return "Student not found", 404  # Return a 404 error if the student is not found

    # Insert visitor record
    cursor.execute("""
        INSERT INTO visitor (visitor_name, gender, contact_no, email, city, state, visiting_SRN, Relation, unit_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (visitor_name, gender, contact_no, email, city, state, srn, relation, unit_no))
    visitor_id = cursor.lastrowid

    # Insert log record with entry time as current time and exit time as NULL
    cursor.execute("""
        INSERT INTO logs (Visitor_ID, student_SRN, entry_time, unit_no)
        VALUES (%s, %s, %s, %s)
    """, (visitor_id, srn, datetime.now(), unit_no))
    
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('security'))


@app.route('/record_exit/<int:log_id>', methods=['POST'])
def record_exit(log_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Update exit time to current time for the given log ID
    cursor.execute("""
        UPDATE logs SET exit_time = %s WHERE log_ID = %s
    """, (datetime.now(), log_id))
    
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('security'))


if __name__ == '__main__':
    app.run(debug=True)
