from flask import Blueprint, request, redirect, session, flash, render_template_string, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        
        # Email & password validation
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email format!', 'error')
            return redirect('/register')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return redirect('/register')
        
        conn = get_db()
        existing = conn.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        if existing:
            flash('Username or email already exists!', 'error')
            conn.close()
            return redirect('/register')
        
        hashed_password = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (username, email, password, phone) VALUES (?, ?, ?, ?)',
            (username, email, hashed_password, phone)
        )
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect('/login')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['logged_in'] = True
            flash('Welcome back!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple admin credentials
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Admin access granted!', 'success')
            return redirect('/admin/dashboard')
        else:
            flash('Invalid admin credentials!', 'error')
    
    return render_template('admin/admin_login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect('/')
