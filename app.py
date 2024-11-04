from flask import Flask, render_template, request, jsonify,redirect,url_for
from db_connection import get_connection

app = Flask(__name__)

# Home route (optional)
@app.route('/')
def home():
    return "Hello"  # Create an index.html if needed

# Route for Student page
@app.route('/student')
def student():
    return render_template('student.html')

# Route for Student complaint page
@app.route('/student/complaint')
def student_complaint():
    return render_template('complaint.html')

# Route for Student update password page
@app.route('/student/update-password')
def student_update_password():
    return render_template('update_password.html')

# Route for Security page
@app.route('/security')
def security():
    return render_template('security.html')

# Route for Maintenance Staff page
@app.route('/maintenance')
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



@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    if request.method == 'POST':
        visitor_name = request.form['visitor_name']
        gender = request.form['gender']
        contact_no = request.form['contact_no']
        email = request.form['email']
        city = request.form['city']
        state = request.form['state']
        visiting_srn = request.form['visiting_srn']
        relation = request.form['relation']
        unit_no = request.form['unit_no']

        db = db_connection()
        cursor = db.cursor()

        # Insert into visitor table
        cursor.execute(
            "INSERT INTO visitor (visitor_name, gender, contact_no, email, city, state, visiting_SRN, Relation, unit_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (visitor_name, gender, contact_no, email, city, state, visiting_srn, relation, unit_no)
        )
        visitor_id = cursor.lastrowid

        # Insert into logs table
        cursor.execute(
            "INSERT INTO logs (Visitor_ID, student_SRN, entry_time, exit_time, unit_no) "
            "VALUES (%s, %s, %s, NULL, %s)",
            (visitor_id, visiting_srn, datetime.now(), unit_no)
        )

        db.commit()
        cursor.close()
        db.close()
        return redirect("/security")

@app.route('/current_visitors')
def current_visitors():
    db = db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT v.visitor_ID, v.visitor_name, l.entry_time, s.student_name, l.unit_no
        FROM logs l
        JOIN visitor v ON l.Visitor_ID = v.visitor_ID
        JOIN students s ON l.student_SRN = s.student_SRN
        WHERE l.exit_time IS NULL
    """)
    current_visitors = cursor.fetchall()
    
    cursor.close()
    db.close()
    return render_template('security.html', current_visitors=current_visitors)

# 3. Record exit time
@app.route('/exit_visitor/<int:visitor_id>', methods=['POST'])
def exit_visitor(visitor_id):
    db = db_connection()
    cursor = db.cursor()

    # Update exit time in logs table
    cursor.execute(
        "UPDATE logs SET exit_time = %s WHERE Visitor_ID = %s AND exit_time IS NULL",
        (datetime.now(), visitor_id)
    )

    db.commit()
    cursor.close()
    db.close()
    return redirect('security.html')
if __name__ == '__main__':
    app.run(debug=True)
