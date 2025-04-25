import psycopg2

def get_connection():
    conn = psycopg2.connect(
        dbname="main",
        user="admin",
        password="admin",
        host="localhost",
        port="5432"
    )
    return conn

