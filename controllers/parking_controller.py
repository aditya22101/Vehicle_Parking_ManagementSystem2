from flask import Blueprint, request, redirect, session, flash, render_template_string
from database import get_db
from datetime import datetime, timedelta

parking_bp = Blueprint('parking', __name__)

def require_login():
    if 'logged_in' not in session:
        flash('Please login first!', 'error')
        return redirect('/login')
    return None

@parking_bp.route('/book/<int:lot_id>', methods=['GET', 'POST'])
def book_slot(lot_id):
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    # Get parking lot details
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ? AND deleted_at IS NULL', (lot_id,)).fetchone()
    if not lot:
        flash('Parking lot not found!', 'error')
        conn.close()
        return redirect('/dashboard')
    
    # Get available slots
    slots = conn.execute('''
        SELECT * FROM parking_slots 
        WHERE parking_lot_id = ? AND status = 'available'
        ORDER BY slot_number
    ''', (lot_id,)).fetchall()
    
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number']
        vehicle_type = request.form['vehicle_type']
        hours = int(request.form['hours'])
        slot_id = int(request.form['slot_id'])
        
        # Verify slot is still available
        slot_check = conn.execute('''
            SELECT * FROM parking_slots 
            WHERE id = ? AND status = 'available'
        ''', (slot_id,)).fetchone()
        
        if not slot_check:
            flash('Selected slot is no longer available!', 'error')
            conn.close()
            return redirect(f'/book/{lot_id}')
        
        # Calculate cost and end time
        total_cost = lot['price_per_hour'] * hours
        end_time = datetime.now() + timedelta(hours=hours)
        
        # Create booking
        cursor = conn.execute('''
            INSERT INTO bookings (user_id, parking_lot_id, slot_id, vehicle_number,
                                vehicle_type, end_time, total_cost, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ''', (session['user_id'], lot_id, slot_id, vehicle_number, vehicle_type,
              end_time, total_cost))
        
        # Update slot status
        conn.execute('''
            UPDATE parking_slots SET status = 'occupied' WHERE id = ?
        ''', (slot_id,))
        
        conn.commit()
        conn.close()
        
        flash(f'Slot #{slot_check["slot_number"]} booked successfully!', 'success')
        return redirect('/my-bookings')
    
    # Generate slots HTML
    slots_html = ''
    for slot in slots:
        slots_html += f'''
        <div class="col-md-2 col-sm-3 col-4 mb-2">
            <div class="card slot-card bg-success text-white text-center"
                 data-slot-id="{slot['id']}" data-slot-number="{slot['slot_number']}"
                 style="cursor: pointer; transition: all 0.3s;">
                <div class="card-body p-2">
                    <i class="fas fa-car"></i><br>
                    <small>Slot {slot['slot_number']}</small>
                </div>
            </div>
        </div>
        '''
    
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Book Slot - ParkEasy</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            .slot-card:hover { transform: scale(1.05); }
            .slot-card.selected { background-color: #007bff !important; border: 2px solid #0056b3; }
        </style>
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-car"></i> ParkEasy</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/dashboard">Dashboard</a>
                    <a class="nav-link" href="/logout">Logout</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row justify-content-center">
                <div class="col-md-10">
                    <div class="card shadow">
                        <div class="card-header bg-primary text-white">
                            <h3><i class="fas fa-calendar-plus"></i> Book Parking Slot</h3>
                        </div>
                        <div class="card-body">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h5><i class="fas fa-building"></i> ''' + lot['name'] + '''</h5>
                                    <p><i class="fas fa-map-marker-alt"></i> ''' + lot['location'] + '''</p>
                                </div>
                                <div class="col-md-6 text-end">
                                    <div class="mb-2">
                                        <span class="badge bg-success">''' + str(len(slots)) + ''' slots available</span>
                                    </div>
                                    <div>
                                        <strong class="text-success">${''' + f'{lot["price_per_hour"]:.2f}' + '''}/hour</strong>
                                    </div>
                                </div>
                            </div>
                            ''' + (f'''
                            <div class="mb-4">
                                <h6><i class="fas fa-th"></i> Available Slots (Click to Select)</h6>
                                <div class="row">
                                    {slots_html}
                                </div>
                            </div>
                            <form method="POST" id="bookingForm">
                                <input type="hidden" id="slot_id" name="slot_id" required>
                                
                                <div class="alert alert-info" id="selectedSlotInfo" style="display: none;">
                                    <strong>Selected Slot:</strong> <span id="selectedSlotNumber"></span>
                                </div>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label">Vehicle Number</label>
                                        <input type="text" class="form-control" name="vehicle_number"
                                               placeholder="e.g., ABC-1234" required>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label">Vehicle Type</label>
                                        <select class="form-control" name="vehicle_type" required>
                                            <option value="">Select Vehicle Type</option>
                                            <option value="car">Car</option>
                                            <option value="motorcycle">Motorcycle</option>
                                            <option value="truck">Truck</option>
                                            <option value="van">Van</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Duration (Hours)</label>
                                    <input type="number" class="form-control" id="hours" name="hours"
                                           min="1" max="24" value="1" required>
                                </div>
                                <div class="mb-4">
                                    <div class="alert alert-info">
                                        <strong>Total Cost:</strong> $<span id="total-cost">{lot['price_per_hour']:.2f}</span>
                                    </div>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <a href="/dashboard" class="btn btn-secondary">
                                        <i class="fas fa-arrow-left"></i> Back
                                    </a>
                                    <button type="submit" class="btn btn-success" id="confirmBtn" disabled>
                                        <i class="fas fa-check"></i> Confirm Booking
                                    </button>
                                </div>
                            </form>
                            ''' if slots else '''
                            <div class="text-center py-4">
                                <i class="fas fa-parking fa-3x text-muted mb-3"></i>
                                <h5>No Available Slots</h5>
                                <p class="text-muted">All parking slots are currently occupied.</p>
                                <a href="/dashboard" class="btn btn-primary">
                                    <i class="fas fa-arrow-left"></i> Back to Dashboard
                                </a>
                            </div>
                            ''') + '''
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script>
        const pricePerHour = ''' + str(lot['price_per_hour']) + ''';
        document.addEventListener('DOMContentLoaded', function() {
            // Handle slot selection
            document.addEventListener('click', function(e) {
                const slotCard = e.target.closest('.slot-card');
                if (slotCard) {
                    // Remove previous selection
                    document.querySelectorAll('.slot-card').forEach(card => {
                        card.classList.remove('selected');
                        card.classList.add('bg-success');
                        card.classList.remove('bg-primary');
                    });
                    
                    // Select new slot
                    slotCard.classList.add('selected');
                    slotCard.classList.remove('bg-success');
                    slotCard.classList.add('bg-primary');
                    
                    // Update form
                    const slotId = slotCard.dataset.slotId;
                    const slotNumber = slotCard.dataset.slotNumber;
                    
                    document.getElementById('slot_id').value = slotId;
                    document.getElementById('selectedSlotNumber').textContent = slotNumber;
                    document.getElementById('selectedSlotInfo').style.display = 'block';
                    document.getElementById('confirmBtn').disabled = false;
                }
            });
            
            // Update cost calculation
            const hoursInput = document.getElementById('hours');
            if (hoursInput) {
                hoursInput.addEventListener('input', function() {
                    const hours = parseFloat(this.value) || 1;
                    const totalCost = (hours * pricePerHour).toFixed(2);
                    document.getElementById('total-cost').textContent = totalCost;
                });
            }
        });
        </script>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

@parking_bp.route('/cancel-booking/<int:booking_id>')
def cancel_booking(booking_id):
    auth_check = require_login()
    if auth_check:
        return auth_check
    
    conn = get_db()
    
    # Get booking details
    booking = conn.execute('''
        SELECT * FROM bookings 
        WHERE id = ? AND user_id = ? AND status = 'active'
    ''', (booking_id, session['user_id'])).fetchone()
    
    if booking:
        # Cancel booking
        conn.execute('''
            UPDATE bookings SET status = 'cancelled' WHERE id = ?
        ''', (booking_id,))
        
        # Free up the slot
        conn.execute('''
            UPDATE parking_slots SET status = 'available' WHERE id = ?
        ''', (booking['slot_id'],))
        
        conn.commit()
        flash('Booking cancelled successfully!', 'success')
    else:
        flash('Booking not found or already cancelled!', 'error')
    
    conn.close()
    return redirect('/my-bookings')

@parking_bp.route('/admin/force-release-slot/<int:slot_id>', methods=['POST'])
def force_release_slot(slot_id):
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')
    
    conn = get_db()
    
    # Get active booking for this slot
    booking = conn.execute('''
        SELECT * FROM bookings 
        WHERE slot_id = ? AND status = 'active'
    ''', (slot_id,)).fetchone()
    
    if booking:
        # Cancel the booking
        conn.execute('''
            UPDATE bookings SET status = 'cancelled' WHERE id = ?
        ''', (booking['id'],))
    
    # Free the slot
    conn.execute('''
        UPDATE parking_slots SET status = 'available' WHERE id = ?
    ''', (slot_id,))
    
    conn.commit()
    conn.close()
    
    flash('Slot released successfully!', 'success')
    return redirect(request.referrer or '/admin/dashboard')
