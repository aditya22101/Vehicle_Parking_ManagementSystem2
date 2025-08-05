from database import get_db
from datetime import datetime

def auto_cancel_expired_bookings():
    """Automatically cancel expired bookings and free up slots"""
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get expired but still active bookings
    expired_bookings = conn.execute('''
        SELECT id, slot_id FROM bookings 
        WHERE end_time < ? AND status = 'active'
    ''', (now,)).fetchall()
    
    for booking in expired_bookings:
        booking_id = booking['id']
        slot_id = booking['slot_id']
        
        # Cancel booking
        conn.execute("UPDATE bookings SET status = 'expired' WHERE id = ?", (booking_id,))
        
        # Free the slot
        conn.execute("UPDATE parking_slots SET status = 'available' WHERE id = ?", (slot_id,))
    
    conn.commit()
    conn.close()
    
    return len(expired_bookings)

def get_booking_statistics():
    """Get booking statistics for dashboard"""
    conn = get_db()
    
    stats = {}
    
    # Total bookings
    stats['total_bookings'] = conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
    
    # Active bookings
    stats['active_bookings'] = conn.execute(
        'SELECT COUNT(*) FROM bookings WHERE status = "active"'
    ).fetchone()[0]
    
    # Today's revenue
    today = datetime.now().strftime('%Y-%m-%d')
    stats['today_revenue'] = conn.execute('''
        SELECT COALESCE(SUM(total_cost), 0) FROM bookings 
        WHERE DATE(created_at) = ? AND status IN ('active', 'completed')
    ''', (today,)).fetchone()[0]
    
    # This month's revenue
    this_month = datetime.now().strftime('%Y-%m')
    stats['month_revenue'] = conn.execute('''
        SELECT COALESCE(SUM(total_cost), 0) FROM bookings 
        WHERE strftime('%Y-%m', created_at) = ? AND status IN ('active', 'completed')
    ''', (this_month,)).fetchone()[0]
    
    conn.close()
    return stats
