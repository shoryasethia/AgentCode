# AgentCode Logging System Documentation

## Overview

AgentCode now uses a unified logging system that stores all logs in the database with session and user context. This replaces console printing with structured, searchable logging.

## Features

- **Database Storage**: All logs stored in SQLite database
- **Session Context**: Logs tied to user sessions and activities
- **User Context**: Logs associated with authenticated users
- **Categorized Logging**: Different categories for different components
- **No Console Noise**: Silent operation, no terminal printing
- **Structured Data**: JSON details for complex log data
- **Performance Optimized**: Database indexes for fast queries

## Log Categories

- `AUTH`: Authentication and authorization events
- `SESSION`: Session management and workspace creation
- `WORKSPACE`: File operations and workspace management  
- `AGENT`: AI agent processing and workflows
- `API`: API requests and responses
- `DATABASE`: Database operations and schema changes
- `SYSTEM`: System startup, configuration, and errors

## Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General information about application flow
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error conditions that don't stop execution
- `CRITICAL`: Critical errors that may stop execution

## Usage in Code

### Basic Logging
```python
from logger import log_info, log_error, LogCategory

# Simple info log
log_info(LogCategory.SYSTEM, "Application started")

# Error with details
log_error(LogCategory.AUTH, "Login failed", {
    'username': username,
    'ip_address': request.remote_addr
})
```

### Setting Context
```python
from logger import set_log_context, clear_log_context

# Set context for a user session
set_log_context(
    session_id="session_123",
    user_id=42,
    username="john_doe",
    request_id="req_456"
)

# Your code here - all logs will include this context

# Clear context when done
clear_log_context()
```

### Advanced Usage
```python
from logger import logger, LogLevel, LogCategory

# Direct logger access
logger.log(
    LogLevel.WARNING, 
    LogCategory.WORKSPACE,
    "File operation took longer than expected",
    details={
        'file_path': '/path/to/file',
        'duration_ms': 2500,
        'operation': 'read'
    },
    session_id="session_123"
)
```

## Viewing Logs

### Command Line Tool
```bash
# View latest 20 logs
python view_logs.py --limit 20

# View logs for specific session
python view_logs.py --session session_1753114781076_4b52010b

# View error logs only
python view_logs.py --level ERROR

# View authentication logs
python view_logs.py --category AUTH

# View logs for specific user
python view_logs.py --user 1
```

### Programmatic Access
```python
from logger import get_session_logs, get_user_logs

# Get logs for a session
session_logs = get_session_logs("session_123", limit=50)

# Get logs for a user
user_logs = get_user_logs(user_id=42, limit=100)
```

## Database Schema

The logging system creates a `logs` table with the following structure:

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    user_id INTEGER,
    username TEXT,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,  -- JSON string
    source_file TEXT,
    function_name TEXT,
    line_number INTEGER,
    request_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## Migration from Print Statements

**Before:**
```python
print(f"User {username} logged in successfully")
```

**After:**
```python
log_info(LogCategory.AUTH, f"User logged in successfully", {
    'username': username,
    'session_id': session_id
})
```

## Best Practices

1. **Use Appropriate Categories**: Choose the right category for each log
2. **Include Context**: Add relevant details in the details dictionary
3. **Set Context Early**: Use `set_log_context()` at the start of request handling
4. **Clear Context**: Always clear context when request is complete
5. **Structured Details**: Use dictionaries for complex data instead of string formatting
6. **Avoid Sensitive Data**: Don't log passwords or sensitive information

## Performance Considerations

- Database indexes on common query fields (session_id, user_id, timestamp, level)
- Logs are written asynchronously to avoid blocking operations
- Automatic cleanup of old logs (implement retention policy as needed)
- Connection pooling for database operations

## Configuration

The logger uses the same database as the main application (`instance/agentcode.db`). No additional configuration is required.

## Troubleshooting

### If logs are not appearing:
1. Check that the database is writable
2. Verify the `logs` table was created
3. Check for database connection errors
4. Ensure proper permissions on the instance directory

### Performance issues:
1. Check database size and consider log rotation
2. Verify indexes are created
3. Monitor database lock contention

## Integration Points

The logging system is integrated into:
- **Flask Auth Server** (`app.py`): Request/response logging, authentication events
- **FastAPI Backend** (`api_server.py`): Agent operations, workspace management
- **Database Manager** (`database.py`): Database operations, user management
- **Agent System**: Task processing, file operations (via imports)

## Future Enhancements

- Web UI for log viewing and filtering
- Real-time log streaming via WebSocket
- Log aggregation and analytics
- Automated alerting on error patterns
- Export functionality for log analysis
