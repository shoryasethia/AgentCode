"""
FastAPI backend for AgentCode IDE
Handles agent communication, file operations, and chat functionality
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import json
import uuid
import traceback
from pathlib import Path
from datetime import datetime
import json
import uuid
from pathlib import Path
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import unified logger and database
from logger import set_log_context, clear_log_context, log_info, log_error, log_warning, LogCategory
from database import DatabaseManager

# Load environment variables
load_dotenv()

# Import our agent system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))

try:
    from agents.main import MainOrchestrator, run_development_workflow
    from agents.state import OverallState, WorkflowConfig
    from agents.config import get_workflow_config # type: ignore
    log_info(LogCategory.SYSTEM, "Agent system imported successfully")
except ImportError as e:
    log_error(LogCategory.SYSTEM, f"Failed to import agent system: {e}")
    # Create fallback functions
    def run_development_workflow(user_task, workspace_path, config):
        return {"response": f"Agent system not available. Task: {user_task}"}
    def get_workflow_config(workspace_path=None):
        return {"max_iterations": 10, "timeout_seconds": 300}
    MainOrchestrator = None
except Exception as e:
    log_error(LogCategory.SYSTEM, f"Error loading agent system: {e}")
    # Create fallback functions
    def run_development_workflow(user_task, workspace_path, config):
        return {"response": f"Agent system error. Task: {user_task}"}
    def get_workflow_config(workspace_path=None):
        return {"max_iterations": 10, "timeout_seconds": 300}
    MainOrchestrator = None

app = FastAPI(title="AgentCode API", version="1.0.0")

# Middleware for logging context
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Set up logging context for each request"""
    request_id = str(uuid.uuid4())
    # Extract session_id from path or query parameters
    session_id = None
    if "/api/workspace/" in str(request.url):
        session_id = str(request.url).split("/api/workspace/")[-1].split("?")[0]
    elif request.query_params.get("session_id"):
        session_id = request.query_params.get("session_id")
    
    set_log_context(request_id=request_id, session_id=session_id)
    
    try:
        response = await call_next(request)
        return response
    finally:
        clear_log_context()

# CORS middleware
cors_origins = [
    "http://localhost:3000", 
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    current_file: Optional[str] = None
    code_content: Optional[str] = None
    cursor_position: Optional[Dict[str, int]] = None
    workspace_path: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    requires_confirmation: bool = False
    proposed_changes: Optional[List[Dict[str, Any]]] = None
    thoughts: Optional[List[str]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class FileOperation(BaseModel):
    operation: str  # "create", "modify", "delete", "read"
    file_path: str
    content: Optional[str] = None
    line_range: Optional[Dict[str, int]] = None

class WorkspaceInfo(BaseModel):
    files: List[Dict[str, Any]]
    directories: List[str]
    total_files: int

class ApplyChangesRequest(BaseModel):
    session_id: str
    approved: bool
    changes: Optional[List[Dict[str, Any]]] = None

# Global storage for sessions (in production, use Redis or database)
active_sessions: Dict[str, Dict[str, Any]] = {}

# Initialize database manager
db_manager = DatabaseManager()

# Initialize agent orchestrator with default config
try:
    if MainOrchestrator and callable(get_workflow_config):
        config = get_workflow_config("./workspaces/default")
        if hasattr(config, '__dict__') or isinstance(config, dict):
            orchestrator = MainOrchestrator(config) # type: ignore
            log_info(LogCategory.SYSTEM, "Agent orchestrator initialized")
        else:
            orchestrator = None
            log_warning(LogCategory.SYSTEM, "Invalid config type, orchestrator not initialized")
    else:
        orchestrator = None
        log_warning(LogCategory.SYSTEM, "Agent orchestrator not available")
except Exception as e:
    log_error(LogCategory.SYSTEM, f"Failed to initialize orchestrator: {e}")
    orchestrator = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.options("/api/chat")
async def chat_options():
    return {"message": "OK"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Main chat endpoint that processes user commands and routes to agent framework
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create or get session
        if session_id not in active_sessions:
            # Create workspace in user's AC directory
            workspace_base = os.path.join(os.path.dirname(__file__), "workspaces")
            os.makedirs(workspace_base, exist_ok=True)
            workspace_path = os.path.join(workspace_base, session_id)
            
            active_sessions[session_id] = {
                "conversation_history": [],
                "current_state": None,
                "workspace_path": workspace_path
            }
            log_info(LogCategory.WORKSPACE, f"Created new session workspace: {workspace_path}", {
                'session_id': session_id,
                'workspace_path': workspace_path
            })
        
        session = active_sessions[session_id]
        
        # Ensure workspace directory exists
        workspace_path = Path(session["workspace_path"])
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Add user message to history
        user_message_data = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat(),
            "context": {
                "current_file": request.current_file,
                "cursor_position": request.cursor_position
            }
        }
        session["conversation_history"].append(user_message_data)
        
        # Create overall state for agent processing
        overall_state = {
            "user_task": request.message,
            "workspace_path": str(workspace_path),
            "session_id": session_id,
            "current_file": request.current_file,
            "code_content": request.code_content
        }
        
        # Process with agent orchestrator
        result = await process_with_agents(overall_state, session)
        
        # Add agent response to history
        ai_response_data = {
            "role": "assistant",
            "content": result["response"],
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "requires_confirmation": result.get("requires_confirmation", False),
                "proposed_changes": result.get("proposed_changes", []),
                "thoughts": result.get("thoughts", [])
            }
        }
        session["conversation_history"].append(ai_response_data)
        
        # Save chat messages to database
        db_manager.save_chat_message(session_id, request.message, result["response"])
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            requires_confirmation=result.get("requires_confirmation", False),
            proposed_changes=result.get("proposed_changes", []),
            thoughts=result.get("thoughts", []),
            tool_calls=result.get("tool_calls", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

async def process_with_agents(state: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process user request through the agent framework
    """
    try:
        # Use the run_development_workflow function
        workspace_path = session["workspace_path"]
        user_task = state["user_task"]
        
        log_info(LogCategory.AGENT, f"Processing task: {user_task}", {
            'workspace_path': workspace_path,
            'session_id': state.get('session_id')
        })
        
        # Get configuration for this session
        workflow_config = get_workflow_config(workspace_path)
        log_info(LogCategory.AGENT, "Workflow config loaded", {
            'config': workflow_config
        })
        
        # Run the workflow
        log_info(LogCategory.AGENT, "Running development workflow...")
        result = run_development_workflow(user_task, workspace_path, workflow_config)
        log_info(LogCategory.AGENT, "Workflow completed", {
            'has_result': bool(result)
        })
        
        # Extract results
        thoughts = []
        tool_calls = []
        proposed_changes = []
        requires_confirmation = True
        
        # Parse agent outputs
        if isinstance(result, dict) and "planner_state" in result and result["planner_state"]:
            planner_state = result["planner_state"]
            if isinstance(planner_state, dict) and "atomic_tasks" in planner_state:
                tasks = planner_state["atomic_tasks"] # type: ignore
                if isinstance(tasks, list):
                    for task in tasks:
                        if isinstance(task, dict):
                            proposed_changes.append({
                                "type": task.get("type", "unknown"),
                                "description": task.get("description", "No description"),
                                "target_files": task.get("target_files", []),
                                "priority": task.get("priority", 1)
                            })
        
        # Check for developer state and files created
        if isinstance(result, dict) and "developer_state" in result and result["developer_state"]:
            dev_state = result["developer_state"]
            if isinstance(dev_state, dict) and "files_created" in dev_state:
                files_created = dev_state["files_created"] # type: ignore
                if isinstance(files_created, list):
                    for file_info in files_created:
                        if isinstance(file_info, dict):
                            proposed_changes.append({
                                "type": "file_created",
                                "description": f"Created file: {file_info.get('name', 'unknown')}",
                                "target_files": [file_info.get('path', '')],
                                "priority": 1
                            })
        
        # Generate response
        if proposed_changes:
            response = f"I've analyzed your request and prepared {len(proposed_changes)} changes. Here's what I'll do:\n\n"
            for i, change in enumerate(proposed_changes, 1):
                response += f"{i}. {change['description']}\n"
            # response += "\nWould you like me to proceed with these changes?"
            requires_confirmation = False  # Auto-apply for now
        else:
            # Check if the result has a direct response
            if isinstance(result, dict) and "response" in result:
                response = result["response"]
            else:
                response = "I understand your request. Let me help you with that."
            requires_confirmation = False
        
        # Store the result in session for later use
        session["last_workflow_result"] = result
        
        return {
            "response": response,
            "requires_confirmation": requires_confirmation,
            "proposed_changes": proposed_changes,
            "thoughts": thoughts,
            "tool_calls": tool_calls
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_error(LogCategory.AGENT, f"Agent processing error: {str(e)}", {
            'error_details': error_details,
            'user_task': state.get('user_task', 'unknown')
        })
        
        return {
            "response": f"Sorry, I encountered an error processing your request. Please try again.",
            "requires_confirmation": False,
            "proposed_changes": [],
            "thoughts": [f"Error: {str(e)}"],
            "tool_calls": []
        }

@app.post("/api/apply-changes")
async def apply_changes(request: ApplyChangesRequest):
    """
    Apply approved changes from the agent
    """
    try:
        if request.session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[request.session_id]
        
        if not request.approved:
            return {"status": "cancelled", "message": "Changes cancelled by user"}
        
        # Apply the changes using the developer agent
        if session.get("current_state") and "developer_state" in session["current_state"]:
            developer_state = session["current_state"]["developer_state"]
            
            # Execute the atomic tasks
            for change in request.changes or []:
                # Here you would implement the actual file operations
                # This is a simplified version
                if change["type"] == "create_file":
                    file_path = Path(session["workspace_path"]) / change["target_files"][0]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    # You would generate the actual content using the developer agent
                    file_path.write_text("# Generated by AgentCode\n")
                elif change["type"] == "modify_file":
                    # Implement file modification logic
                    pass
        
        return {"status": "success", "message": "Changes applied successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying changes: {str(e)}")

@app.get("/api/workspace/{session_id}", response_model=WorkspaceInfo)
async def get_workspace_info(session_id: str):
    """
    Get workspace file structure
    """
    try:
        # Determine workspace path
        workspace_path = None
        
        # First check if session is in memory
        if session_id in active_sessions:
            session = active_sessions[session_id]
            workspace_path = Path(session.get("workspace_path", "."))
        else:
            # Session not in memory, check if workspace directory exists on filesystem
            workspaces_dir = Path("workspaces")
            potential_workspace = workspaces_dir / session_id
            if potential_workspace.exists():
                workspace_path = potential_workspace
                # Add session back to active_sessions for future requests
                active_sessions[session_id] = {
                    "workspace_path": str(workspace_path),
                    "created_at": datetime.now().isoformat()
                }
                log_info(LogCategory.WORKSPACE, f"Restored session from filesystem: {session_id}", {
                    'session_id': session_id,
                    'workspace_path': str(workspace_path)
                })
        
        # If no workspace path found, return empty
        if not workspace_path or not workspace_path.exists():
            return WorkspaceInfo(
                files=[],
                directories=[],
                total_files=0
            )
        
        files = []
        directories = []
        
        for item in workspace_path.rglob("*"):
            if item.is_file():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(workspace_path)),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            elif item.is_dir():
                directories.append(str(item.relative_to(workspace_path)))
        
        return WorkspaceInfo(
            files=files,
            directories=directories,
            total_files=len(files)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workspace info: {str(e)}")

@app.post("/api/file-operation")
async def file_operation(operation: FileOperation, session_id: str):
    """
    Perform file operations (create, read, modify, delete)
    """
    try:
        log_info(LogCategory.API, f"File operation requested: {operation.operation}", {
            'session_id': session_id,
            'file_path': operation.file_path,
            'operation': operation.operation
        })
        
        # Check if session exists in memory, if not try to restore it
        if session_id not in active_sessions:
            log_warning(LogCategory.SESSION, f"Session not in memory, attempting to restore: {session_id}")
            
            # Try to restore session from filesystem
            workspaces_dir = Path("workspaces")
            potential_workspace = workspaces_dir / session_id
            if potential_workspace.exists():
                # Load chat history from database
                chat_history = db_manager.get_chat_history(session_id)
                
                active_sessions[session_id] = {
                    "workspace_path": str(potential_workspace),
                    "conversation_history": chat_history,
                    "current_state": None
                }
                log_info(LogCategory.SESSION, f"Session restored from filesystem with chat history: {session_id}", {
                    'chat_messages': len(chat_history)
                })
            else:
                log_error(LogCategory.SESSION, f"Session not found and workspace doesn't exist: {session_id}")
                raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[session_id]
        workspace_path = Path(session["workspace_path"])
        file_path = workspace_path / operation.file_path
        
        log_info(LogCategory.WORKSPACE, f"File operation: {operation.operation} on {file_path}")
        
        # Security check - ensure file is within workspace
        if not str(file_path.resolve()).startswith(str(workspace_path.resolve())):
            log_error(LogCategory.WORKSPACE, f"Security violation: file outside workspace", {
                'file_path': str(file_path),
                'workspace_path': str(workspace_path)
            })
            raise HTTPException(status_code=403, detail="Access denied - file outside workspace")
        
        if operation.operation == "read":
            if not file_path.exists():
                log_error(LogCategory.WORKSPACE, f"File not found: {file_path}")
                raise HTTPException(status_code=404, detail="File not found")
            content = file_path.read_text(encoding='utf-8')
            log_info(LogCategory.WORKSPACE, f"File read successfully: {file_path}", {
                'file_size': len(content)
            })
            return {"content": content}
        
        elif operation.operation == "create":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(operation.content or "", encoding='utf-8')
            log_info(LogCategory.WORKSPACE, f"File created: {file_path}")
            return {"status": "created"}
        
        elif operation.operation == "modify":
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            file_path.write_text(operation.content or "", encoding='utf-8')
            log_info(LogCategory.WORKSPACE, f"File modified: {file_path}")
            return {"status": "modified"}
        
        elif operation.operation == "delete":
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            file_path.unlink()
            log_info(LogCategory.WORKSPACE, f"File deleted: {file_path}")
            return {"status": "deleted"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid operation")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing file operation: {str(e)}")

@app.get("/api/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get chat history for a session
    """
    try:
        log_info(LogCategory.API, f"Chat history requested for session: {session_id}")
        
        # Check if session exists in memory, if not try to restore it
        if session_id not in active_sessions:
            log_warning(LogCategory.SESSION, f"Session not in memory, attempting to restore: {session_id}")
            
            # Try to restore session from filesystem
            workspaces_dir = Path("workspaces")
            potential_workspace = workspaces_dir / session_id
            if potential_workspace.exists():
                # Load chat history from database
                chat_history = db_manager.get_chat_history(session_id)
                
                active_sessions[session_id] = {
                    "workspace_path": str(potential_workspace),
                    "conversation_history": chat_history,
                    "current_state": None
                }
                log_info(LogCategory.SESSION, f"Session restored with chat history: {session_id}", {
                    'chat_messages': len(chat_history)
                })
            else:
                log_error(LogCategory.SESSION, f"Session not found and workspace doesn't exist: {session_id}")
                return {"conversation_history": [], "total_messages": 0}
        
        session = active_sessions[session_id]
        
        # If conversation_history is empty, try to load from database
        if not session.get("conversation_history"):
            chat_history = db_manager.get_chat_history(session_id)
            session["conversation_history"] = chat_history
            log_info(LogCategory.SESSION, f"Loaded chat history from database: {len(chat_history)} messages")
        conversation_history = session.get("conversation_history", [])
        
        log_info(LogCategory.API, f"Retrieved chat history: {len(conversation_history)} messages", {
            'session_id': session_id,
            'message_count': len(conversation_history)
        })
        
        return {
            "conversation_history": conversation_history,
            "total_messages": len(conversation_history),
            "session_id": session_id
        }
        
    except Exception as e:
        log_error(LogCategory.API, f"Error retrieving chat history: {str(e)}", {
            'session_id': session_id,
            'error': str(e)
        })
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")

@app.delete("/api/chat-history/{session_id}")
async def clear_chat_history(session_id: str):
    """
    Clear chat history for a session
    """
    try:
        log_info(LogCategory.API, f"Clear chat history requested for session: {session_id}")
        
        # Clear from database
        success = db_manager.clear_chat_history(session_id)
        
        if success:
            # Also clear from active session if it exists
            if session_id in active_sessions:
                active_sessions[session_id]["conversation_history"] = []
                log_info(LogCategory.SESSION, f"Cleared active session chat history: {session_id}")
            
            log_info(LogCategory.API, f"Chat history cleared successfully for session: {session_id}")
            return {"status": "success", "message": "Chat history cleared"}
        else:
            log_warning(LogCategory.API, f"Failed to clear chat history for session: {session_id}")
            raise HTTPException(status_code=500, detail="Failed to clear chat history")
        
    except Exception as e:
        log_error(LogCategory.API, f"Error clearing chat history: {str(e)}", {
            'session_id': session_id,
            'error': str(e)
        })
        raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")

@app.get("/api/sessions")
async def get_active_sessions():
    """
    Get list of active sessions (for debugging)
    """
    return {
        "active_sessions": len(active_sessions),
        "sessions": [
            {
                "id": sid,
                "workspace": session["workspace_path"],
                "messages": len(session["conversation_history"])
            }
            for sid, session in active_sessions.items()
        ]
    }

@app.get("/api/download-workspace/{session_id}")
async def download_workspace(session_id: str):
    """
    Get workspace location for download
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    workspace_path = session["workspace_path"]
    
    # List all files in workspace
    files = []
    if os.path.exists(workspace_path):
        for root, dirs, filenames in os.walk(workspace_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, workspace_path)
                files.append({
                    "name": filename,
                    "path": rel_path,
                    "full_path": file_path,
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                })
    
    return {
        "workspace_location": os.path.abspath(workspace_path),
        "files": files,
        "total_files": len(files),
        "message": f"Files are stored at: {os.path.abspath(workspace_path)}"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
