import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'parking-app-secret-key-2024'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'parking_system.db'
    
    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # App settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Pagination
    BOOKINGS_PER_PAGE = 20
    
    # Auto-refresh intervals (in seconds)
    DASHBOARD_REFRESH_INTERVAL = 30
    USER_DASHBOARD_REFRESH_INTERVAL = 60
