import hashlib
from multiprocessing import connection
from flask import Flask
from flask import render_template, jsonify, make_response, redirect, request, session, url_for
from flask_bootstrap import Bootstrap

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from numpy import identity

import random
import string
import hashlib

import sqlite3

app = Flask(__name__)
Bootstrap(app)

app.secret_key = "iO1K3FqsIFnQ7n3e1eQx3L7I2JVdMXaZO8PAdqLl"

app.config["JWT_SECRET_KEY"] = "emNtAK1iFSzr2yOV4N1a4ebPojVU2CV6fIhhIrJT"
app.config['JWT_TOKEN_LOCATION'] = ['cookies']

jwt = JWTManager(app)

current_sessions = []

#setup sqlite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    connection = get_db_connection()
    with open('seed.sql') as f:
        connection.executescript(f.read())
    connection.commit()
    connection.close()

def check_session():
    """check required param is in session
    add a user to users if not"""
    if "userid" not in session:
        print("new session")
        tmp_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

        while tmp_id in current_sessions:
            tmp_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

        session["userid"] = tmp_id
        print(tmp_id)

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users WHERE username = ?", (session["userid"],)).fetchall()
    print("Users")
    print(users)
    # print(users[0]["username"])
    # print(users[0])
    if len(users) < 1:
        print("adding")
        hash = hashlib.md5(session["userid"].encode('utf-8')).hexdigest()
        print(hash)
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (session["userid"], hash))
        conn.commit()
    
    conn.close()

@app.route("/")
def index():
    """list all challenges"""
    check_session()

    return render_template("index.html")

@app.route("/xss2")
def xss2():
    """alert the cookie via reflected"""
    check_session()

    if request.args.get("flavour") and request.args.get("quantity"):
        return render_template("xss2.html", order=True, flavour=request.args.get("flavour"), quantity=request.args.get("quantity"))
    else:
        return render_template("xss2.html")

@app.route("/xss1")
def xss1():
    """alert the cookie via stored + redirect user to their page"""
    check_session()

    conn = get_db_connection()
    comments = conn.execute("SELECT * FROM comments WHERE userid = ?", (session["userid"],)).fetchall()

    if len(comments) > 0:
        return render_template("xss1.html", comments=comments)
    else:
        return render_template("xss1.html")

@app.route("/xss1/comment", methods=["POST"])
def insert_comment():
    """insert a comment"""
    check_session()

    conn = get_db_connection()
    conn.execute('INSERT INTO comments (comment, userid) VALUES (?, ?)', (request.form.get("comment"), session["userid"]))
    conn.commit()
    conn.close()

    return redirect("/xss1")


@app.route("/xss1/clear", methods=["POST"])
def clear_comments():
    """clear all comments for user"""
    check_session()
    conn = get_db_connection()
    conn.execute("DELETE FROM comments WHERE userid = ?", (session["userid"],))
    conn.commit()
    conn.close()

    return redirect("/xss1")

@app.route("/sqli1")
def sqli1():
    """SQLi to login"""
    check_session()

    return render_template("sqli1.html")

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = hashlib.md5(request.form['password'].encode('utf-8')).hexdigest()
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT id, username FROM users WHERE username='{username}' AND password='{password}'")
    users = cur.fetchall()
    
    if len(users) > 0:
        # session['SESH_id'], session['SESH_username'] = users[0]
        return redirect(url_for("admin", allowed=True))
    else:
        print("Wrong username or password")
        full_sql_command = f"SELECT id, username FROM users WHERE username='{username}' AND password='{password}'"
        return render_template("sqli1.html", error="Wrong email or password", full_sql_command=full_sql_command)

@app.route("/admin")
def admin():
    if not request.args.get("allowed"):
        return redirect("/sqli1")
    else:
        return render_template("admin.html")

@app.route("/sqli2")
def sqli2():
    """SQLi to dump creds"""
    check_session()

    return render_template("sqli2.html", currusername=session["userid"])

@app.route("/sqli2/getuserdata")
def getuserdata():
    print("getuserdata")
    check_session()

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    users = cur.execute(f"SELECT * FROM users WHERE username = '" + request.args.get("userid") + "'").fetchall()

    print("second users")
    print(users)

    return render_template("sqli2.html", user=users[0])

@app.route("/cookies")
def cookies():
    """edit cookie to isAdmin=True"""
    check_session()

    if request.cookies.get('isAdmin') == "True":
        resp = make_response(render_template("cookies.html", successful=True))
        resp.set_cookie('isAdmin', '', expires=0)
        return resp
    else:
        resp = make_response(render_template("cookies.html"))
        resp.set_cookie('isAdmin', "False")
        return resp

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000)