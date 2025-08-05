from flask import Blueprint, request, redirect, session, flash, render_template, jsonify, make_response
from database import get_db
from datetime import datetime, timedelta
import csv
import io

admin_bp = Blueprint('admin', __name__)

def require_admin():
    if 'admin_logged_in' not in session:
        flash('Admin access required!', 'error')
        return redirect('/admin/login')
    return None

@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    # Get statistics
    stats = {}
    stats['total_lots'] = conn.execute('SELECT COUNT(*) FROM parking_lots WHERE deleted_at IS NULL').fetchone()[0]
    stats['total_slots'] = conn.execute('SELECT COUNT(*) FROM parking_slots ps JOIN parking_lots pl ON ps.parking_lot_id = pl.id WHERE pl.deleted_at IS NULL').fetchone()[0]
    stats['available_slots'] = conn.execute('SELECT COUNT(*) FROM parking_slots ps JOIN parking_lots pl ON ps.parking_lot_id = pl.id WHERE ps.status = "available" AND pl.deleted_at IS NULL').fetchone()[0]
    stats['occupied_slots'] = conn.execute('SELECT COUNT(*) FROM parking_slots ps JOIN parking_lots pl ON ps.parking_lot_id = pl.id WHERE ps.status = "occupied" AND pl.deleted_at IS NULL').fetchone()[0]
    stats['total_revenue'] = conn.execute('SELECT COALESCE(SUM(total_cost), 0) FROM bookings WHERE status IN ("active", "completed")').fetchone()[0]
    
    # Get parking lots with slot counts
    lots = conn.execute('''
        SELECT p.*, 
               COUNT(ps.id) as total_slots,
               SUM(CASE WHEN ps.status = 'available' THEN 1 ELSE 0 END) as available_slots,
               SUM(CASE WHEN ps.status = 'occupied' THEN 1 ELSE 0 END) as occupied_slots
        FROM parking_lots p
        LEFT JOIN parking_slots ps ON p.id = ps.parking_lot_id
        WHERE p.deleted_at IS NULL
        GROUP BY p.id
        ORDER BY p.name
    ''').fetchall()
    
    # Get chart data for dashboard
    chart_data = get_dashboard_chart_data(conn)
    
    conn.close()
    return render_template('admin/dashboard.html', stats=stats, lots=lots, chart_data=chart_data)

@admin_bp.route('/admin/add-lot', methods=['GET', 'POST'])
def add_lot():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        total_slots = int(request.form['total_slots'])
        price_per_hour = float(request.form['price_per_hour'])
        
        conn = get_db()
        cursor = conn.execute('''
            INSERT INTO parking_lots (name, location, total_slots, price_per_hour)
            VALUES (?, ?, ?, ?)
        ''', (name, location, total_slots, price_per_hour))
        
        lot_id = cursor.lastrowid
        
        # Create slots for the lot
        for slot_num in range(1, total_slots + 1):
            conn.execute('''
                INSERT INTO parking_slots (parking_lot_id, slot_number, status)
                VALUES (?, ?, 'available')
            ''', (lot_id, slot_num))
        
        conn.commit()
        conn.close()
        
        flash(f'Parking lot "{name}" created successfully with {total_slots} slots!', 'success')
        return redirect('/admin/dashboard')
    
    return render_template('admin/add_lot.html')

@admin_bp.route('/admin/edit-lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        price_per_hour = float(request.form['price_per_hour'])
        
        conn.execute('''
            UPDATE parking_lots 
            SET name = ?, location = ?, price_per_hour = ?
            WHERE id = ?
        ''', (name, location, price_per_hour, lot_id))
        
        conn.commit()
        conn.close()
        
        flash('Parking lot updated successfully!', 'success')
        return redirect('/admin/dashboard')
    
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ? AND deleted_at IS NULL', (lot_id,)).fetchone()
    conn.close()
    
    if not lot:
        flash('Parking lot not found!', 'error')
        return redirect('/admin/dashboard')
    
    return render_template('admin/edit_lot.html', lot=lot)

@admin_bp.route('/admin/delete-lot/<int:lot_id>')
def delete_lot(lot_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    # Soft delete - mark as deleted instead of actually deleting
    conn.execute('''
        UPDATE parking_lots 
        SET deleted_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (lot_id,))
    
    conn.commit()
    conn.close()
    
    flash('Parking lot deleted successfully!', 'success')
    return redirect('/admin/dashboard')

@admin_bp.route('/admin/bookings')
def all_bookings():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    # Get search parameters
    search_user = request.args.get('search_user', '')
    search_lot = request.args.get('search_lot', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    conn = get_db()
    
    # Build query with filters
    query = '''
        SELECT b.*, u.username, u.email, p.name as lot_name, p.location, ps.slot_number
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN parking_lots p ON b.parking_lot_id = p.id
        JOIN parking_slots ps ON b.slot_id = ps.id
        WHERE 1=1
    '''
    params = []
    
    if search_user:
        query += ' AND (u.username LIKE ? OR u.email LIKE ?)'
        params.extend([f'%{search_user}%', f'%{search_user}%'])
    
    if search_lot:
        query += ' AND p.name LIKE ?'
        params.append(f'%{search_lot}%')
    
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
    
    return render_template('admin/bookings.html', bookings=bookings, 
                         search_user=search_user, search_lot=search_lot, 
                         status_filter=status_filter, date_from=date_from, date_to=date_to)

@admin_bp.route('/admin/slot-map/<int:lot_id>')
def slot_map(lot_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ? AND deleted_at IS NULL', (lot_id,)).fetchone()
    if not lot:
        flash('Parking lot not found!', 'error')
        return redirect('/admin/dashboard')
    
    slots = conn.execute('''
        SELECT ps.*, b.vehicle_number, b.end_time
        FROM parking_slots ps
        LEFT JOIN bookings b ON ps.id = b.slot_id AND b.status = 'active'
        WHERE ps.parking_lot_id = ?
        ORDER BY ps.slot_number
    ''', (lot_id,)).fetchall()
    
    conn.close()
    
    return render_template('admin/slot_map.html', lot=lot, slots=slots)

@admin_bp.route('/admin/export-csv')
def export_csv():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    export_type = request.args.get('type', 'bookings')
    
    conn = get_db()
    
    if export_type == 'bookings':
        data = conn.execute('''
            SELECT b.id, u.username, u.email, p.name as lot_name, p.location,
                   ps.slot_number, b.vehicle_number, b.vehicle_type,
                   b.start_time, b.end_time, b.total_cost, b.status
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN parking_lots p ON b.parking_lot_id = p.id
            JOIN parking_slots ps ON b.slot_id = ps.id
            ORDER BY b.created_at DESC
        ''').fetchall()
        
        filename = f'bookings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        headers = ['ID', 'Username', 'Email', 'Parking Lot', 'Location', 'Slot', 
                  'Vehicle Number', 'Vehicle Type', 'Start Time', 'End Time', 'Cost', 'Status']
    
    elif export_type == 'lots':
        data = conn.execute('''
            SELECT p.id, p.name, p.location, p.total_slots, p.price_per_hour,
                   COUNT(ps.id) as actual_slots,
                   SUM(CASE WHEN ps.status = 'available' THEN 1 ELSE 0 END) as available,
                   SUM(CASE WHEN ps.status = 'occupied' THEN 1 ELSE 0 END) as occupied
            FROM parking_lots p
            LEFT JOIN parking_slots ps ON p.id = ps.parking_lot_id
            WHERE p.deleted_at IS NULL
            GROUP BY p.id
        ''').fetchall()
        
        filename = f'parking_lots_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        headers = ['ID', 'Name', 'Location', 'Total Slots', 'Price/Hour', 
                  'Actual Slots', 'Available', 'Occupied']
    
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for row in data:
        writer.writerow(row)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@admin_bp.route('/admin/deleted-lots')
def deleted_lots():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    deleted_lots = conn.execute('''
        SELECT * FROM parking_lots 
        WHERE deleted_at IS NOT NULL 
        ORDER BY deleted_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/deleted_lots.html', deleted_lots=deleted_lots)

@admin_bp.route('/admin/restore-lot/<int:lot_id>')
def restore_lot(lot_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = get_db()
    conn.execute('UPDATE parking_lots SET deleted_at = NULL WHERE id = ?', (lot_id,))
    conn.commit()
    conn.close()
    
    flash('Parking lot restored successfully!', 'success')
    return redirect('/admin/deleted-lots')

@admin_bp.route('/admin/api/dashboard-data')
def dashboard_api():
    auth_check = require_admin()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    chart_data = get_dashboard_chart_data(conn)
    conn.close()
    
    return jsonify(chart_data)

def get_dashboard_chart_data(conn):
    # Revenue by day (last 7 days)
    revenue_data = conn.execute('''
        SELECT DATE(created_at) as date, SUM(total_cost) as revenue
        FROM bookings 
        WHERE created_at >= date('now', '-7 days')
        AND status IN ('active', 'completed')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''').fetchall()
    
    # Bookings by status
    status_data = conn.execute('''
        SELECT status, COUNT(*) as count
        FROM bookings
        GROUP BY status
    ''').fetchall()
    
    # Occupancy by parking lot
    occupancy_data = conn.execute('''
        SELECT p.name, 
               COUNT(ps.id) as total_slots,
               SUM(CASE WHEN ps.status = 'occupied' THEN 1 ELSE 0 END) as occupied_slots
        FROM parking_lots p
        LEFT JOIN parking_slots ps ON p.id = ps.parking_lot_id
        WHERE p.deleted_at IS NULL
        GROUP BY p.id, p.name
    ''').fetchall()
    
    return {
        'revenue': [{'date': row['date'], 'revenue': float(row['revenue'] or 0)} for row in revenue_data],
        'status': [{'status': row['status'], 'count': row['count']} for row in status_data],
        'occupancy': [{'name': row['name'], 'total': row['total_slots'], 'occupied': row['occupied_slots']} for row in occupancy_data]
    }
