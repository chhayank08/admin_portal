from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from flask_cors import CORS
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'ae03f0a92a4339bc6bdc4ef710ce43b3'  # Change this to a random secret key
CORS(app)

# Database connection configuration
DATABASE = {
    'dbname': 'sparrow_admin_portal',
    'user': 'postgres',
    'password': 'root1234',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    conn = psycopg2.connect(
        dbname=DATABASE['dbname'],
        user=DATABASE['user'],
        password=DATABASE['password'],
        host=DATABASE['host'],
        port=DATABASE['port']
    )
    return conn

# Create tables if they do not exist
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inside_server (
            s_no SERIAL PRIMARY KEY,
            service_name VARCHAR(100) NOT NULL,
            users INTEGER,
            hostname VARCHAR(100) NOT NULL,
            status VARCHAR(50),
            url VARCHAR(100) NOT NULL,
            server_ip_public_ip BYTEA,
            apache VARCHAR(200) NOT NULL,
            doc_server_db_server VARCHAR(100) NOT NULL,
            db_name VARCHAR(100) NOT NULL
        )
    ''')
    cursor.execute('''
           CREATE TABLE IF NOT EXISTS outside_server (
            s_no SERIAL PRIMARY KEY,
            service_name VARCHAR(100) NOT NULL,
            users INTEGER,
            hostname VARCHAR(100) NOT NULL,
            status VARCHAR(50),
            url VARCHAR(100) NOT NULL,
            server_ip_public_ip BYTEA,
            apache VARCHAR(200) NOT NULL,
            doc_server_db_server VARCHAR(100) NOT NULL,
            db_name VARCHAR(100) NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

create_tables()

# Dummy user for demonstration purposes
USER = {
    'username': 'admin',
    'password': generate_password_hash('admin1234')  # Hashed password for 'admin1234'
}

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/inside_server')
def index():
    if 'username' in session:
        return render_template('inside_server.html')
    return redirect(url_for('login'))

@app.route('/get_data', methods=['GET'])
def get_data():
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT s_no, service_name, users, hostname, status, url, server_ip_public_ip, apache, doc_server_db_server, db_name FROM inside_server')
        data = cursor.fetchall()
        columns = ['s_no', 'service_name', 'users', 'hostname', 'status', 'url', 'server_ip_public_ip', 'apache', 'doc_server_db_server', 'db_name']
        servers_with_files = [dict(zip(columns, row)) for row in data]
        cursor.close()
        conn.close()
        return jsonify(servers_with_files)
    return redirect(url_for('login'))

@app.route('/get_outside_data', methods=['GET'])
def get_outside_data():
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT s_no, service_name, users, hostname, status, url, server_ip_public_ip, apache, doc_server_db_server, db_name FROM outside_server')
        data = cursor.fetchall()
        columns = ['s_no', 'service_name', 'users', 'hostname', 'status', 'url', 'server_ip_public_ip', 'apache', 'doc_server_db_server', 'db_name']
        servers_with_files = [dict(zip(columns, row)) for row in data]
        cursor.close()
        conn.close()
        return jsonify(servers_with_files)
    return redirect(url_for('login'))

@app.route('/add_inside_server', methods=['POST'])
def add_inside_server():
    if 'username' in session:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO inside_server (service_name, hostname, url, server_ip_public_ip, apache, doc_server_db_server, db_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (data['service_name'], data['hostname'], data['url'], data['server_ip_public_ip'], data['apache'], data['doc_server_db_server'], data['db_name']))
            conn.commit()
            return 'Inside Server added successfully!', 200
        except Exception as e:
            conn.rollback()
            return str(e), 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))


@app.route('/add_outside_server', methods=['POST'])
def add_outside_server():
    if 'username' in session:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO outside_server (service_name, hostname, url, server_ip_public_ip, apache, doc_server_db_server, db_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (data['service_name'], data['hostname'], data['url'], data['server_ip_public_ip'], data['apache'], data['doc_server_db_server'], data['db_name']))
            conn.commit()
            return 'Outside Server added successfully!', 200
        except Exception as e:
            conn.rollback()
            return str(e), 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

# File Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'username' in session:
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                flash('File successfully uploaded', 'success')
                return redirect(url_for('view_uploads'))
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload>
        </form>
        '''
    return redirect(url_for('login'))


@app.route('/uploads')
def view_uploads():
    if 'username' in session:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        return render_template('uploads.html', files=files)
    return redirect(url_for('login'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if 'username' in session:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
