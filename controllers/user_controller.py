from flask import Blueprint, request, redirect, session, flash, render_template_string, render_template
from database import get_db
from utils.booking_utils import auto_cancel_expired_bookings
from datetime import datetime

user_bp = Blueprint('user', __name__)

def require_login():
    if 'logged_in' not in session:
        flash('Please login first!', 'error')
        return redirect('/login')
    return None

@user_bp.route('/dashboard')
def dashboard():
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    # Auto-cancel expired bookings
    auto_cancel_expired_bookings()
    
    conn = get_db()
    
    # Get search parameters
    search_location = request.args.get('search_location', '')
    max_price = request.args.get('max_price', '')
    
    # Build query with filters
    query = '''
        SELECT p.*,
               COUNT(ps.id) as total_slots,
               SUM(CASE WHEN ps.status = 'available' THEN 1 ELSE 0 END) as available_slots
        FROM parking_lots p
        LEFT JOIN parking_slots ps ON p.id = ps.parking_lot_id
        WHERE p.deleted_at IS NULL
    '''
    params = []
    
    if search_location:
        query += ' AND (p.name LIKE ? OR p.location LIKE ?)'
        params.extend([f'%{search_location}%', f'%{search_location}%'])
    
    if max_price:
        query += ' AND p.price_per_hour <= ?'
        params.append(float(max_price))
    
    query += '''
        GROUP BY p.id
        HAVING available_slots > 0
        ORDER BY p.name
    '''
    
    lots = conn.execute(query, params).fetchall()
    conn.close()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('user/dashboard.html', lots=lots, current_time=current_time,
                         search_location=search_location, max_price=max_price)

@user_bp.route('/my-bookings')
def my_bookings():
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    # Get search parameters
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    conn = get_db()
    
    # Build query with filters
    query = '''
        SELECT b.*, p.name as lot_name, p.location, ps.slot_number
        FROM bookings b
        JOIN parking_lots p ON b.parking_lot_id = p.id
        JOIN parking_slots ps ON b.slot_id = ps.id
        WHERE b.user_id = ?
    '''
    params = [session['user_id']]
    
    if status_filter:
        query += ' AND b.status = ?'
        params.append(status_filter)
    
    if date_from:
        query += ' AND DATE(b.created_at) >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND DATE(b.created_at) <= ?'
        params.append(date_to)
    
    query += ' ORDER BY b.created_at DESC'
    
    bookings = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('user/my_bookings.html', bookings=bookings,
                         status_filter=status_filter, date_from=date_from, date_to=date_to)

@user_bp.route('/slot-map/<int:lot_id>')
def user_slot_map(lot_id):
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ? AND deleted_at IS NULL', (lot_id,)).fetchone()
    if not lot:
        flash('Parking lot not found!', 'error')
        return redirect('/dashboard')
    
    slots = conn.execute('''
        SELECT ps.*, 
               CASE WHEN b.id IS NOT NULL THEN b.end_time ELSE NULL END as occupied_until
        FROM parking_slots ps
        LEFT JOIN bookings b ON ps.id = b.slot_id AND b.status = 'active'
        WHERE ps.parking_lot_id = ?
        ORDER BY ps.slot_number
    ''', (lot_id,)).fetchall()
    
    conn.close()
    
    return render_template('user/slot_map.html', lot=lot, slots=slots)
