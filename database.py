"""
Database initialization and management for AgentCode
"""
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib
from datetime import datetime

# Import the unified logger
from logger import log_info, log_error, log_warning, LogCategory, set_log_context

class DatabaseManager:
    """Manages SQLite database operations for AgentCode"""
    
    def __init__(self, db_path: str = "instance/agentcode.db"):
        self.db_path = Path(db_path)
        # Ensure instance directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        self.connection = None
        
    def connect(self):
        """Create connection to the database"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def database_exists(self) -> bool:
        """Check if database file exists"""
        return self.db_path.exists()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists in the database"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    
    def create_tables(self):
        """Create all necessary tables if they don't exist"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Users table
        if not self.table_exists('users'):
            log_info(LogCategory.DATABASE, "Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            log_info(LogCategory.DATABASE, "Users table created successfully")
        else:
            log_warning(LogCategory.DATABASE, "Users table already exists, skipping creation")
        
        # Sessions table
        if not self.table_exists('sessions'):
            log_info(LogCategory.DATABASE, "Creating sessions table...")
            cursor.execute("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    workspace_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_current BOOLEAN DEFAULT 0,
                    session_name TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            log_info(LogCategory.DATABASE, "Sessions table created successfully")
        else:
            log_warning(LogCategory.DATABASE, "Sessions table already exists, skipping creation")
            # Check if we need to add new columns to existing table
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_current' not in columns:
                log_info(LogCategory.DATABASE, "Adding is_current column to sessions table...")
                cursor.execute("ALTER TABLE sessions ADD COLUMN is_current BOOLEAN DEFAULT 0")
                conn.commit()
                log_info(LogCategory.DATABASE, "Added is_current column successfully")
            
            if 'session_name' not in columns:
                log_info(LogCategory.DATABASE, "Adding session_name column to sessions table...")
                cursor.execute("ALTER TABLE sessions ADD COLUMN session_name TEXT")
                conn.commit()
                log_info(LogCategory.DATABASE, "Added session_name column successfully")
        
        # Workspaces table
        if not self.table_exists('workspaces'):
            log_info(LogCategory.DATABASE, "Creating workspaces table...")
            cursor.execute("""
                CREATE TABLE workspaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            log_info(LogCategory.DATABASE, "Workspaces table created successfully")
        else:
            log_warning(LogCategory.DATABASE, "Workspaces table already exists, skipping creation")
        
        # Chat history table
        if not self.table_exists('chat_history'):
            log_info(LogCategory.DATABASE, "Creating chat_history table...")
            cursor.execute("""
                CREATE TABLE chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT,
                    ai_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            log_info(LogCategory.DATABASE, "Chat history table created successfully")
        else:
            log_warning(LogCategory.DATABASE, "Chat history table already exists, skipping creation")
        
        conn.commit()
        log_info(LogCategory.DATABASE, "Database schema initialization complete!")
    
    def initialize_default_users(self):
        """
        Check if any users exist in the database.
        No default users are created - users must register manually.
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        # Check if users already exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        
        if user_count == 0:
            log_info(LogCategory.DATABASE, "No users found in database. Users must register manually.")
            log_info(LogCategory.DATABASE, "Use the registration form to create your first account.")
        else:
            log_info(LogCategory.DATABASE, f"Database contains {user_count} registered users")
    
    def check_user_exists(self, username: Optional[str] = None, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if user already exists by username or email
        Returns (exists, reason)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        if username:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = ?", (username,))
            if cursor.fetchone()['count'] > 0:
                return True, "username"
        
        if email:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = ?", (email,))
            if cursor.fetchone()['count'] > 0:
                return True, "email"
        
        return False, ""
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None
    
    def create_user(self, username: str, password: str, name: str, email: str) -> Tuple[bool, str]:
        """
        Create a new user with duplicate prevention
        Returns (success, message)
        """
        try:
            # Check for duplicates first
            exists, reason = self.check_user_exists(username, email)
            if exists:
                message = f"User with this {reason} already exists"
                log_warning(LogCategory.AUTH, f"Duplicate user creation attempt: {username} ({email})", {
                    'username': username,
                    'email': email,
                    'duplicate_field': reason
                })
                return False, message
            
            conn = self.connect()
            cursor = conn.cursor()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, password_hash, name, email, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash, name, email, datetime.now()))
            conn.commit()
            
            # Get the created user ID
            user_id = cursor.lastrowid
            
            log_info(LogCategory.AUTH, f"User created successfully: {username}", {
                'user_id': user_id,
                'username': username,
                'name': name,
                'email': email
            })
            return True, "User created successfully"
            
        except sqlite3.IntegrityError as e:
            message = "User creation failed due to constraint violation"
            log_error(LogCategory.AUTH, f"User creation failed: {username}", {
                'username': username,
                'email': email,
                'error': str(e)
            })
            return False, message
        except Exception as e:
            message = f"User creation failed: {str(e)}"
            log_error(LogCategory.AUTH, f"Unexpected error creating user: {username}", {
                'username': username,
                'error': str(e)
            })
            return False, message
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials"""
        user = self.get_user_by_username(username)
        if user:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user['password_hash'] == password_hash:
                # Update last login
                conn = self.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE username = ?
                """, (username,))
                conn.commit()
                return user
        return None
    
    def create_session(self, user_id: int, session_name: Optional[str] = None) -> str:
        """Create a new session for a user and set it as current"""
        import uuid
        import time
        
        session_id = f"session_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"
        if not session_name:
            session_name = f"Session {int(time.time())}"
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Set all existing sessions for this user as not current
        cursor.execute("""
            UPDATE sessions SET is_current = 0 
            WHERE user_id = ?
        """, (user_id,))
        
        # Create new session
        cursor.execute("""
            INSERT INTO sessions (id, user_id, session_name, is_current, is_active)
            VALUES (?, ?, ?, 1, 1)
        """, (session_id, user_id, session_name))
        
        conn.commit()
        log_info(LogCategory.SESSION, f"Created new session: {session_id} for user {user_id}", {
            'session_id': session_id,
            'user_id': user_id,
            'session_name': session_name
        })
        return session_id
    
    def get_current_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the current session for a user"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE user_id = ? AND is_current = 1 AND is_active = 1
            ORDER BY last_activity DESC
            LIMIT 1
        """, (user_id,))
        session = cursor.fetchone()
        return dict(session) if session else None
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE user_id = ? AND is_active = 1
            ORDER BY last_activity DESC
        """, (user_id,))
        sessions = cursor.fetchall()
        return [dict(session) for session in sessions]
    
    def set_current_session(self, user_id: int, session_id: str) -> bool:
        """Set a session as current for a user"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # First, unset all current sessions for this user
        cursor.execute("""
            UPDATE sessions SET is_current = 0 
            WHERE user_id = ?
        """, (user_id,))
        
        # Set the specified session as current
        cursor.execute("""
            UPDATE sessions SET is_current = 1, last_activity = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (session_id, user_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    def update_session_activity(self, session_id: str):
        """Update the last activity timestamp for a session"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET last_activity = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (session_id,))
        conn.commit()
    
    def save_chat_message(self, session_id: str, user_message: str, ai_response: Optional[str] = None) -> bool:
        """Save a chat message to the database"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_history (session_id, user_message, ai_response, timestamp)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_message, ai_response, datetime.now()))
            conn.commit()
            
            log_info(LogCategory.DATABASE, f"Chat message saved for session: {session_id}", {
                'session_id': session_id,
                'has_user_message': bool(user_message),
                'has_ai_response': bool(ai_response)
            })
            return True
        except Exception as e:
            log_error(LogCategory.DATABASE, f"Failed to save chat message: {str(e)}", {
                'session_id': session_id,
                'error': str(e)
            })
            return False
    
    def get_chat_history(self, session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve chat history for a session"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_id, user_message, ai_response, timestamp 
                FROM chat_history 
                WHERE session_id = ? 
                ORDER BY timestamp ASC 
                LIMIT ? OFFSET ?
            """, (session_id, limit, offset))
            
            chat_history = []
            for row in cursor.fetchall():
                message = dict(row)
                # Convert to the format expected by the frontend
                if message['user_message']:
                    chat_history.append({
                        'role': 'user',
                        'content': message['user_message'],
                        'timestamp': message['timestamp']
                    })
                if message['ai_response']:
                    chat_history.append({
                        'role': 'assistant',
                        'content': message['ai_response'],
                        'timestamp': message['timestamp']
                    })
            
            log_info(LogCategory.DATABASE, f"Retrieved chat history: {len(chat_history)} messages", {
                'session_id': session_id,
                'message_count': len(chat_history)
            })
            return chat_history
            
        except Exception as e:
            log_error(LogCategory.DATABASE, f"Failed to retrieve chat history: {str(e)}", {
                'session_id': session_id,
                'error': str(e)
            })
            return []
    
    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for a session"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            conn.commit()
            
            log_info(LogCategory.DATABASE, f"Chat history cleared for session: {session_id}", {
                'session_id': session_id,
                'rows_deleted': cursor.rowcount
            })
            return True
        except Exception as e:
            log_error(LogCategory.DATABASE, f"Failed to clear chat history: {str(e)}", {
                'session_id': session_id,
                'error': str(e)
            })
            return False
    
    def get_or_create_session(self, user_id: int) -> str:
        """Get current session or create a new one if none exists"""
        current_session = self.get_current_session(user_id)
        if current_session:
            return current_session['id']
        else:
            return self.create_session(user_id)


def initialize_database(db_path: str = "instance/agentcode.db") -> DatabaseManager:
    """
    Initialize the AgentCode database.
    If database already exists, it will not create a new one.
    """
    db_manager = DatabaseManager(db_path)
    
    if db_manager.database_exists():
        log_info(LogCategory.DATABASE, f"Database already exists at: {db_manager.db_path.absolute()}")
        log_info(LogCategory.DATABASE, "Checking schema and ensuring all tables exist...")
    else:
        log_info(LogCategory.DATABASE, f"Creating new database at: {db_manager.db_path.absolute()}")
    
    # Create tables (only if they don't exist)
    db_manager.create_tables()
    
    # Check user status (no default users created)
    db_manager.initialize_default_users()
    
    return db_manager


if __name__ == "__main__":
    # Initialize database when run directly
    print("🚀 Initializing AgentCode Database...")
    db_manager = initialize_database()
    print("✅ Database initialization complete!")
    db_manager.close()
