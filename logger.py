"""
Unified Logging System for AgentCode
Provides session-based and user-based logging with database persistence
"""

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import threading
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    AUTH = "AUTH"
    SESSION = "SESSION"
    WORKSPACE = "WORKSPACE"
    AGENT = "AGENT"
    API = "API"
    DATABASE = "DATABASE"
    SYSTEM = "SYSTEM"

class AgentCodeLogger:
    """
    Centralized logging system for AgentCode
    Logs to database with session and user context
    """
    
    def __init__(self, db_path: str = "instance/agentcode.db"):
        self.db_path = Path(db_path)
        self.thread_local = threading.local()
        self._ensure_log_table()
        
        # Configure Python logging to not print to console
        logging.getLogger().handlers = []  # Remove all handlers
        logging.basicConfig(level=logging.CRITICAL + 1)  # Disable console logging
    
    def _ensure_log_table(self):
        """Ensure the logs table exists in the database"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        user_id INTEGER,
                        username TEXT,
                        level TEXT NOT NULL,
                        category TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        source_file TEXT,
                        function_name TEXT,
                        line_number INTEGER,
                        request_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_session ON logs(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
                
                conn.commit()
        except Exception as e:
            print(f"Failed to create logs table: {e}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def set_context(self, session_id: Optional[str] = None, user_id: Optional[int] = None, 
                   username: Optional[str] = None, request_id: Optional[str] = None):
        """Set logging context for current thread"""
        self.thread_local.session_id = session_id
        self.thread_local.user_id = user_id
        self.thread_local.username = username
        self.thread_local.request_id = request_id
    
    def clear_context(self):
        """Clear logging context for current thread"""
        self.thread_local.session_id = None
        self.thread_local.user_id = None
        self.thread_local.username = None
        self.thread_local.request_id = None
    
    def _get_caller_info(self):
        """Get information about the calling function"""
        import inspect
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the actual caller (skip logger methods)
            for i in range(10):  # Reasonable limit
                if frame is None:
                    break
                frame = frame.f_back
                if frame is None:
                    break
                
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno
                
                # Skip internal logger methods
                if not filename.endswith('logger.py'):
                    return {
                        'source_file': Path(filename).name,
                        'function_name': function_name,
                        'line_number': line_number
                    }
            
            return {'source_file': 'unknown', 'function_name': 'unknown', 'line_number': 0}
        finally:
            del frame
    
    def log(self, level: LogLevel, category: LogCategory, message: str, 
           details: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None,
           user_id: Optional[int] = None, username: Optional[str] = None):
        """
        Log a message with full context
        """
        try:
            # Use provided context or thread-local context
            ctx_session_id = session_id or getattr(self.thread_local, 'session_id', None)
            ctx_user_id = user_id or getattr(self.thread_local, 'user_id', None)
            ctx_username = username or getattr(self.thread_local, 'username', None)
            ctx_request_id = getattr(self.thread_local, 'request_id', None)
            
            # Get caller information
            caller_info = self._get_caller_info()
            
            # Prepare details as JSON
            details_json = json.dumps(details) if details else None
            
            # Insert log entry
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO logs (
                        session_id, user_id, username, level, category, message, 
                        details, source_file, function_name, line_number, request_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ctx_session_id, ctx_user_id, ctx_username, level.value, 
                    category.value, message, details_json,
                    caller_info['source_file'], caller_info['function_name'], 
                    caller_info['line_number'], ctx_request_id
                ))
                conn.commit()
                
        except Exception as e:
            # Fallback to console if database logging fails
            print(f"Logger error: {e} | Original message: {message}")
    
    def debug(self, category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        self.log(LogLevel.DEBUG, category, message, details, **kwargs)
    
    def info(self, category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        self.log(LogLevel.INFO, category, message, details, **kwargs)
    
    def warning(self, category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        self.log(LogLevel.WARNING, category, message, details, **kwargs)
    
    def error(self, category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        self.log(LogLevel.ERROR, category, message, details, **kwargs)
    
    def critical(self, category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        self.log(LogLevel.CRITICAL, category, message, details, **kwargs)
    
    def get_logs(self, session_id: Optional[str] = None, user_id: Optional[int] = None,
                level: Optional[LogLevel] = None, category: Optional[LogCategory] = None,
                limit: int = 100, offset: int = 0) -> list:
        """
        Retrieve logs with filtering options
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                conditions = []
                params = []
                
                if session_id:
                    conditions.append("session_id = ?")
                    params.append(session_id)
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if level:
                    conditions.append("level = ?")
                    params.append(level.value)
                
                if category:
                    conditions.append("category = ?")
                    params.append(category.value)
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                query = f"""
                    SELECT * FROM logs 
                    {where_clause}
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"Error retrieving logs: {e}")
            return []


# Global logger instance
logger = AgentCodeLogger()

# Convenience functions for easy use throughout the application
def set_log_context(session_id: Optional[str] = None, user_id: Optional[int] = None, 
                   username: Optional[str] = None, request_id: Optional[str] = None):
    """Set logging context for current thread"""
    logger.set_context(session_id, user_id, username, request_id)

def clear_log_context():
    """Clear logging context"""
    logger.clear_context()

def log_debug(category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
    logger.debug(category, message, details, **kwargs)

def log_info(category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
    logger.info(category, message, details, **kwargs)

def log_warning(category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
    logger.warning(category, message, details, **kwargs)

def log_error(category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
    logger.error(category, message, details, **kwargs)

def log_critical(category: LogCategory, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
    logger.critical(category, message, details, **kwargs)

def get_session_logs(session_id: str, limit: int = 100):
    """Get logs for a specific session"""
    return logger.get_logs(session_id=session_id, limit=limit)

def get_user_logs(user_id: int, limit: int = 100):
    """Get logs for a specific user"""
    return logger.get_logs(user_id=user_id, limit=limit)
