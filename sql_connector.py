import pymysql.cursors
import os
from dotenv import load_dotenv
load_dotenv()
try:
    # Attempt to connect to the database using pymysql
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_DATABASE'),
        cursorclass=pymysql.cursors.DictCursor
    )

    # Check if connection is established
    if connection.open:
        print("Connection to MySQL established successfully.")
    with connection.cursor() as my_cursor:
        my_cursor.execute("SET GLOBAL max_allowed_packet=67108864;")

except pymysql.MySQLError as e:
    print("Error while connecting to MySQL:", e)


