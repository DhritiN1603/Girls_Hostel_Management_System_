from flask import Flask,redirect , url_for,render_template
from sql_connector import *

app = Flask(__name__)

@app.route("/",methods=["POST","GET"])
def landing():
    return render_template("landing.html")
@app.route("/login",methods=["POST","GET"])
def login():
    return render_template("login.html")

@app.route("/signup",methods=["POST","GET"])
def signup():
    return render_template("signup.html")

@app.route("/home",methods=["POST","GET"])
def home():
    return render_template("admin_home.html")
if __name__== "__main__":
    app.run(debug=True)

