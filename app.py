from flask import Flask, render_template
from controllers.auth_controller import auth_bp
from controllers.user_controller import user_bp
from controllers.admin_controller import admin_bp
from controllers.parking_controller import parking_bp
from database import init_db

app = Flask(__name__)
app.secret_key = 'parking-app-secret-key-2024'

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(parking_bp)

@app.route('/')
def index():
    return render_template('main.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
