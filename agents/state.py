# state.py
from __future__ import annotations
from typing import TypedDict, Sequence, Optional, List, Dict, Any
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from enum import Enum


class TaskType(str, Enum):
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    CREATE_DIRECTORY = "create_directory"
    MODIFY_FUNCTION = "modify_function"
    ADD_DEPENDENCY = "add_dependency"
    REFACTOR_CODE = "refactor_code"
    ADD_TESTS = "add_tests"
    FIX_BUG = "fix_bug"


class AtomicTask(TypedDict):
    id: str
    description: str
    type: TaskType
    target_files: List[str]
    prerequisites: List[str]
    success_criteria: str
    priority: int
    estimated_complexity: int  # 1-10 scale


class ResearchQuery(TypedDict):
    query: str
    type: str  # "internal", "external", "documentation"
    priority: int
    context: str


class SearchResult(TypedDict):
    query: str
    results: List[Dict[str, Any]]
    source: str  # "internal", "external", "documentation"
    timestamp: str
    relevance_score: float


class PlannerState(TypedDict, total=False):
    # Input
    user_task: str
    workspace_path: str
    
    # Research Phase
    research_queries: Annotated[Sequence[BaseMessage], add_messages]
    internal_search_results: Annotated[Sequence[BaseMessage], add_messages]
    external_search_results: Annotated[Sequence[BaseMessage], add_messages]
    scraped_content: Annotated[Sequence[BaseMessage], add_messages]
    
    # Understanding Phase
    research_conclusions: Annotated[Sequence[BaseMessage], add_messages]
    is_research_sufficient: bool
    understanding_summary: str
    
    # Planning Phase
    atomic_tasks: List[AtomicTask]
    current_planning_step: int
    planning_rationale: str
    task_dependencies: Dict[str, List[str]]
    
    # State Management
    iteration_count: int
    max_iterations: int
    current_phase: str  # "research", "understanding", "planning", "complete"


class DeveloperState(TypedDict, total=False):
    # Input from Planner
    atomic_tasks: List[AtomicTask]
    workspace_path: str
    
    # Current Task Processing
    current_task: Optional[AtomicTask]
    current_task_index: int
    
    # Research for Current Task
    task_research_queries: Annotated[Sequence[BaseMessage], add_messages]
    task_internal_search: Annotated[Sequence[BaseMessage], add_messages]
    task_external_search: Annotated[Sequence[BaseMessage], add_messages]
    
    # Implementation
    implementation_plan: str
    code_changes: List[Dict[str, Any]]
    files_modified: List[str]
    files_created: List[str]
    files_deleted: List[str]
    
    # Validation
    task_completion_status: Dict[str, bool]  # task_id -> completed
    validation_results: Annotated[Sequence[BaseMessage], add_messages]
    errors_encountered: List[str]
    
    # State Management
    current_phase: str  # "research", "implementation", "validation", "complete"
    retry_count: int
    max_retries: int


class SearchConfig(TypedDict):
    internal_enabled: bool
    external_enabled: bool
    max_results_per_query: int
    relevance_threshold: float
    search_timeout: int


class WorkflowConfig(TypedDict):
    model_name: str
    temperature: float
    max_iterations: int
    workspace_path: str
    search_config: SearchConfig
    logging_level: str
    # CORRECTED: Added the missing key to the type definition.
    max_retries: int


class OverallState(TypedDict):
    # Global Configuration
    user_task: str
    workspace_path: str
    config: WorkflowConfig
    
    # Cross-Service Communication
    planner_state: PlannerState
    developer_state: DeveloperState
    
    # Overall Progress
    current_service: str  # "planner", "developer", "complete"
    overall_progress: float  # 0.0 to 1.0
    session_id: str
    
    # Logging and Feedback
    execution_log: Annotated[Sequence[BaseMessage], add_messages]
    feedback_messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Final Results
    completed_tasks: List[AtomicTask]
    final_summary: str
    success: bool