from flask import Flask,redirect , url_for,render_template, request , session
from sql_connector import get_connection
import pymysql

app = Flask(__name__)
app.secret_key="dbms_ghms"
connection = get_connection()
@app.route("/",methods=["POST","GET"])
def landing():
    
    return render_template("landing.html")

@app.route("/login",methods=["POST","GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if connection:
            try:
                with connection.cursor() as my_cursor:
                    my_cursor.execute(
                        "SELECT role FROM login_cred WHERE username = %s AND password = %s",
                        (username, password)
                    )
                    result = my_cursor.fetchone()

                    if result:
                        if result.get('role') == 'Admin' and role=='1': 
                            return redirect(url_for('admin_dashboard')) 
                        elif result.get('role')== 'Student' and role=='2':
                            return redirect(url_for('admin_dashboard'))
                        elif result.get('role')== 'Security' and role=='3':
                            return redirect(url_for('admin_dashboard')) 
                        elif result.get('role')== 'Maintenance' and role=='4':
                            return redirect(url_for('admin_dashboard'))
                        else:
                            print("You do not have the required permissions to access this page.")
                    else:
                        print("Invalid username or password. Please try again.")

            finally:
                my_cursor.close()
        else:
            print("Failed to connect to the database.")
    return render_template("login.html")

@app.route("/signup",methods=["POST","GET"])
def signup():
    if request.method == "POST":
        # Get form data
        full_name = request.form.get("fname")
        srn = request.form.get("srn")
        semester = request.form.get("sem")
        unit = request.form.get("unit")

        # Establish a database connection again , incase directly signup page instead of login
        connection= get_connection()
        if connection:
            try:
                with connection.cursor() as my_cursor:
                    # Insert data into the `registered` table in mysql
                    sql_query = """
                    INSERT INTO registered (fname, srn, sem, unit) 
                    VALUES (%s, %s, %s, %s)
                    """
                    my_cursor.execute(sql_query, (full_name, srn, semester, unit))
                    connection.commit()  # Commiting so that it can be inserted into the table. Important*

                    print("Registration successful. You can now log in once room alloted.")
                    return redirect(url_for('login'))
            except Exception as e:
                print("An error occurred during signup. Please try again.")
                print("Error:", e)
            finally:
                my_cursor.close()
        else:
            print("Failed to connect to the database.")

    return render_template("signup.html")

#all the required routes for admin ( WARDEN )
#---------------------------------------------

@app.route("/admin/home",methods=["POST","GET"])
def admin_dashboard():
    try:
        # Fetch the latest 5 announcements
        with connection.cursor() as cursor:
            sql = "SELECT title, description, date_posted FROM announcements ORDER BY date_posted DESC LIMIT 5"
            cursor.execute(sql)
            announcements = cursor.fetchall()

    except Exception as e:
        print(f"An error occurred while fetching announcements: {e}", "danger")
        announcements = []
    cursor.close()
    return render_template("admin/admin_home.html", announcements=announcements)

@app.route("/admin/announcements",methods=["POST","GET"])
def announcements():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        date_posted = request.form.get("date")  # Assuming date is in 'YYYY-MM-DD' format

        if title and description and date_posted:
            try:
                # Using existing connection
                with connection.cursor() as cursor:
                    # Insert data into the announcements table
                    sql = "INSERT INTO announcements (title, description, date_posted) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (title, description, date_posted))
                    connection.commit()
                    print("Announcement added successfully!", "success")
            except Exception as e:
                print(f"An error occurred: {e}", "danger")
            cursor.close()
    return render_template("admin/announcements.html")

@app.route("/admin/registered",methods=["POST","GET"])
def registered_students():
    return render_template("admin/registered.html")

@app.route("/admin/complaints",methods=["POST","GET"])
def complaints():
    return render_template("admin/complaints.html")

@app.route("/admin/create_user",methods=["POST","GET"])
def create_user():
    return render_template("admin/create_user.html")

@app.route("/admin/menu",methods=["POST","GET"])
def menu():
    try:
        with connection.cursor() as cursor:
            sql="SELECT day, breakfast, lunch, snacks, dinner FROM menu ORDER By id"
            cursor.execute(sql)
        
            menu_items = cursor.fetchall()
            print(menu_items)
            return render_template('admin/menu.html', menu_items=menu_items)
        cursor.close()
    except pymysql.MySQLError as e:
        return f"An error occurred: {e}"
    


#------------------------X---------------------X---------------------


#general logout for everyone 
@app.route("/logout",methods=["POST","GET"])
def logout():
    return render_template("landing.html")

if __name__== "__main__":
    app.run(debug=True)

