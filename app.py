"""
AgentCode Flask Authentication Server
Handles user authentication with persistent database storage
"""
from flask import Flask, jsonify, request, session
from flask_cors import CORS
import os
import secrets
import uuid
from database import initialize_database
from logger import set_log_context, clear_log_context, log_info, log_error, log_warning, LogCategory

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://localhost:5173"])

# Initialize database
log_info(LogCategory.SYSTEM, "Initializing AgentCode Database...")
db_manager = initialize_database()
log_info(LogCategory.SYSTEM, "Database ready!")

@app.before_request
def before_request():
    """Set up logging context for each request"""
    request_id = str(uuid.uuid4())
    user_id = session.get('user', {}).get('id') if 'user' in session else None
    username = session.get('user', {}).get('username') if 'user' in session else None
    set_log_context(request_id=request_id, user_id=user_id, username=username)

@app.after_request  
def after_request(response):
    """Clean up logging context after each request"""
    clear_log_context()
    return response

@app.route("/")
def home():
    return jsonify({
        "status": "AgentCode Authentication Server is running",
        "version": "1.0.0",
        "endpoints": ["/auth", "/login", "/logout", "/register", "/health"]
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "database": "connected"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        log_warning(LogCategory.AUTH, "Login attempt with missing credentials", {
            'username': username,
            'has_password': bool(password)
        })
        return jsonify({"success": False, "message": "Username and password required"}), 400
    
    # Verify user with database
    user = db_manager.verify_user(username, password)
    if user:
        # Get or create current session for user
        session_id = db_manager.get_or_create_session(user['id'])
        
        session['user'] = {
            "id": user['id'],
            "username": user['username'],
            "name": user['name'],
            "email": user['email']
        }
        session['session_id'] = session_id
        
        # Update log context with user info
        set_log_context(session_id=session_id, user_id=user['id'], username=user['username'])
        
        log_info(LogCategory.AUTH, f"User logged in successfully: {username}", {
            'user_id': user['id'],
            'session_id': session_id
        })
        
        return jsonify({
            "success": True, 
            "message": "Login successful",
            "user": session['user'],
            "session_id": session_id
        })
    else:
        log_warning(LogCategory.AUTH, f"Failed login attempt for username: {username}")
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    username = session.get('user', {}).get('username', 'unknown')
    session_id = session.get('session_id')
    
    log_info(LogCategory.AUTH, f"User logged out: {username}", {
        'session_id': session_id
    })
    
    session.pop('user', None)
    session.pop('session_id', None)
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    
    if not all([username, password, name, email]):
        log_warning(LogCategory.AUTH, "Registration attempt with missing fields", {
            'username': username,
            'email': email,
            'name': name,
            'has_password': bool(password)
        })
        return jsonify({"success": False, "message": "All fields required"}), 400
    
    # Create user in database with duplicate prevention
    success, message = db_manager.create_user(username, password, name, email)
    
    if success:
        # Automatically log in the new user
        user = db_manager.get_user_by_username(username)
        if user:
            # Create session for the new user
            session_id = db_manager.get_or_create_session(user['id'])
            
            session['user'] = {
                "id": user['id'],
                "username": user['username'],
                "name": user['name'],
                "email": user['email']
            }
            session['session_id'] = session_id
            
            return jsonify({
                "success": True, 
                "message": "Registration successful! You are now logged in.",
                "user": session['user'],
                "session_id": session_id
            })
        else:
            log_error(LogCategory.AUTH, "Failed to retrieve user after registration", {
                'username': username
            })
            return jsonify({"success": True, "message": "Registration successful, please login"})
    else:
        return jsonify({"success": False, "message": message}), 400

@app.route("/sessions", methods=["GET"])
def get_sessions():
    user = session.get('user')
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    user_sessions = db_manager.get_user_sessions(user['id'])
    current_session = db_manager.get_current_session(user['id'])
    
    return jsonify({
        "success": True,
        "sessions": user_sessions,
        "current_session": current_session
    })

@app.route("/sessions/new", methods=["POST"])
def create_new_session():
    user = session.get('user')
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    data = request.get_json()
    session_name = data.get('session_name') if data else None
    
    new_session_id = db_manager.create_session(user['id'], session_name)
    session['session_id'] = new_session_id
    
    return jsonify({
        "success": True,
        "session_id": new_session_id,
        "message": "New session created"
    })

@app.route("/sessions/<session_id>/activate", methods=["POST"])
def activate_session(session_id):
    user = session.get('user')
    if not user:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    if db_manager.set_current_session(user['id'], session_id):
        session['session_id'] = session_id
        return jsonify({"success": True, "message": "Session activated"})
    else:
        return jsonify({"success": False, "message": "Session not found"}), 404

@app.route("/auth", methods=["GET"])
def check_auth():
    user = session.get('user')
    if user:
        # Get current session
        current_session = db_manager.get_current_session(user['id'])
        session_id = current_session['id'] if current_session else db_manager.get_or_create_session(user['id'])
        session['session_id'] = session_id
        
        return jsonify({
            "authenticated": True, 
            "user": user,
            "session_id": session_id
        })
    return jsonify({"authenticated": False})

if __name__ == "__main__":
    port = int(os.environ.get('FLASK_PORT', 5000))
    print(f"🌟 Starting AgentCode Authentication Server on port {port}")
    print(f"🔗 Server URL: http://localhost:{port}")
    print("💡 Register new users via the application interface")
    app.run(host="0.0.0.0", port=port, debug=True)
