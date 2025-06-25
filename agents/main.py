# main.py

import os
import uuid
import sys
import argparse
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

# Use the config.py module as the source of truth for configuration
import config as app_config
from state import (
    OverallState, PlannerState, DeveloperState,
    WorkflowConfig, AtomicTask, TaskType
)

from planner.planner import create_planner_service
from developer.developer import create_developer_service


class MainOrchestrator:
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.llm = ChatGoogleGenerativeAI(
            model=config["model_name"],
            temperature=config["temperature"],
        )
        self.planner_graph = create_planner_service(self.llm)
        self.developer_graph = create_developer_service(self.llm)

    def initialize_session(self, state: OverallState) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        planner_state = PlannerState(
            user_task=state["user_task"],
            workspace_path=state["workspace_path"],
            atomic_tasks=[],
            max_iterations=self.config["max_iterations"]
        )
        developer_state = DeveloperState(
            atomic_tasks=[],
            workspace_path=state["workspace_path"],
            max_retries=self.config.get("max_retries", 3)
        )
        init_message = HumanMessage(content=f"Session initialized for task: {state['user_task']}")
        return {
            **state, "session_id": session_id, "planner_state": planner_state,
            "developer_state": developer_state, "current_service": "planner",
            "execution_log": [init_message], "completed_tasks": [],
        }

    def run_planner(self, state: OverallState) -> Dict[str, Any]:
        print("\n--- Running Planner ---")
        result = self.planner_graph.invoke(state["planner_state"])
        atomic_tasks = result.get("atomic_tasks", [])
        
        if atomic_tasks:
            print(f"[DEBUG] Planner produced {len(atomic_tasks)} task(s).")
            print(f"[DEBUG] Tasks: {atomic_tasks[0].get('description')}")
        else:
            print(f"[DEBUG] Planner failed to produce a valid plan. The orchestrator will create a recovery task.")

        log_message = AIMessage(content=f"Planner phase complete. Found {len(atomic_tasks)} tasks.")
        return { **state, "planner_state": result, "execution_log": list(state["execution_log"]) + [log_message] }

    def prepare_developer(self, state: OverallState) -> Dict[str, Any]:
        print("\n--- Preparing Developer ---")
        atomic_tasks = state["planner_state"].get("atomic_tasks", [])
        print(f"[DEBUG] Preparing developer with {len(atomic_tasks)} task(s).")
        updated_developer_state = {**state["developer_state"], "atomic_tasks": atomic_tasks}
        return {**state, "developer_state": updated_developer_state}

    def run_developer(self, state: OverallState) -> Dict[str, Any]:
        print("\n--- Running Developer ---")
        developer_state = state["developer_state"]
        if not developer_state.get("atomic_tasks"):
            print("[DEBUG] Developer has no tasks to run. Finalizing.")
            return {**state, "current_service": "complete"}
            
        result = self.developer_graph.invoke(developer_state)
        completed_tasks = [t for t in result.get("atomic_tasks", []) if result.get("task_completion_status", {}).get(t["id"])]
        return {
            **state, "developer_state": result,
            "completed_tasks": completed_tasks, "current_service": "complete"
        }

    def finalize_session(self, state: OverallState) -> Dict[str, Any]:
        print("\n--- Finalizing Session ---")
        dev_state = state.get("developer_state", {})
        completed_count = len(state.get("completed_tasks", []))
        total_tasks = len(dev_state.get("atomic_tasks", []))
        files_created = dev_state.get("files_created", [])
        files_modified = dev_state.get("files_modified", [])
        errors = dev_state.get("errors_encountered", [])
        success = completed_count > 0 and not errors
        summary = f"""
Development Session Complete:
- Task: {state['user_task']}
- Workspace: {state['workspace_path']}
- Tasks Completed: {completed_count}/{total_tasks}
- Success: {success}
- Files Created ({len(files_created)}): {', '.join(files_created) or 'None'}
- Files Modified ({len(files_modified)}): {', '.join(files_modified) or 'None'}
- Errors Encountered ({len(errors)}): {', '.join(errors) or 'None'}
        """.strip()
        return {**state, "final_summary": summary, "success": success}

    def route_after_planner(self, state: OverallState) -> str:
        """
        Decides the next step after the planner. If the planner failed, it creates
        a single, comprehensive recovery task for the developer.
        """
        if state.get("planner_state", {}).get("atomic_tasks"):
            print("[DEBUG] Planner provided a plan. Preparing developer.")
            return "prepare_developer"
        else:
            print("[INFO] Planner failed to create a detailed plan. Creating a single, comprehensive task for the developer to attempt the full request.")
            
            user_task = state['user_task']
            
            # Heuristic to guess target files for web-related tasks
            if any(keyword in user_task.lower() for keyword in ['website', 'html', 'css', 'js']):
                target_files = ["index.html", "style.css", "script.js"]
            else:
                target_files = ["main.py"]
            
            # Create a single recovery task
            recovery_task = AtomicTask(
                id=str(uuid.uuid4()),
                description=f"Planner failed. Implement the user's entire request in the target file(s): '{user_task}'",
                type=TaskType.CREATE_FILE,
                target_files=target_files,
                prerequisites=[],
                success_criteria="The user's request is fully implemented in the specified files.",
                priority=1,
                estimated_complexity=8,
            )
            
            # Inject the recovery task into the state
            state["planner_state"]["atomic_tasks"] = [recovery_task]
            return "prepare_developer"

    def create_main_graph(self):
        workflow = StateGraph(OverallState)
        workflow.add_node("initialize", self.initialize_session)
        workflow.add_node("run_planner", self.run_planner)
        workflow.add_node("prepare_developer", self.prepare_developer)
        workflow.add_node("run_developer", self.run_developer)
        workflow.add_node("finalize", self.finalize_session)
        
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "run_planner")
        
        # This conditional edge now includes the intelligent recovery logic
        workflow.add_conditional_edges(
            "run_planner",
            self.route_after_planner,
            {
                "prepare_developer": "prepare_developer",
                "finalize": "finalize" # This path is unlikely to be taken now, but kept for safety
            }
        )
        
        workflow.add_edge("prepare_developer", "run_developer")
        workflow.add_edge("run_developer", "finalize")
        workflow.add_edge("finalize", END)
        return workflow.compile()

def run_development_workflow(user_task: str, workspace_path: str, config: WorkflowConfig) -> Dict[str, Any]:
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    orchestrator = MainOrchestrator(config)
    main_graph = orchestrator.create_main_graph()
    initial_state = {
        "user_task": user_task, "workspace_path": str(workspace.absolute()), "config": config
    }
    return main_graph.invoke(initial_state)

if __name__ == "__main__":
    if not app_config.GOOGLE_API_KEY:
        sys.exit("Error: GOOGLE_API_KEY not set. Please create a .env file and add GOOGLE_API_KEY='your-key-here'")

    parser = argparse.ArgumentParser(description="AI Development Workflow")
    parser.add_argument("task", help="The development task to accomplish")
    parser.add_argument("workspace", nargs='?', default=app_config.DEFAULT_WORKSPACE_PATH, help=f"Path to workspace directory (default: {app_config.DEFAULT_WORKSPACE_PATH})")
    parser.add_argument("--model", default=app_config.GEMINI_MODEL, help=f"LLM model (default: {app_config.GEMINI_MODEL})")
    parser.add_argument("--temperature", type=float, default=app_config.TEMPERATURE, help=f"LLM temperature (default: {app_config.TEMPERATURE})")
    args = parser.parse_args()

    final_config = app_config.get_workflow_config(args.workspace)
    final_config["model_name"] = args.model
    final_config["temperature"] = args.temperature

    print("Starting development workflow...")
    print(f"Task: {args.task}")
    print(f"Workspace: {final_config['workspace_path']}")
    print(f"Model: {final_config['model_name']}")
    print("-" * 50)

    try:
        result = run_development_workflow(args.task, args.workspace, final_config)
        print("\n" + "=" * 50)
        print("WORKFLOW COMPLETE")
        print("=" * 50)
        print(result.get('final_summary', 'No summary available.'))
        sys.exit(0 if result.get('success') else 1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)