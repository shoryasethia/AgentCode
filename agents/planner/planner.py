# planner/planner.py

import json
import uuid
import re
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from state import PlannerState, AtomicTask, TaskType

class PlannerAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    def generate_plan(self, state: PlannerState) -> Dict[str, Any]:
        """
        Generates a detailed, step-by-step plan of atomic tasks to accomplish the user's request.
        """
        system_prompt = """You are an expert AI software architect. Your sole responsibility is to break down a user's request into a precise, step-by-step list of tasks.

        You must analyze the user's request and create a JSON array of "AtomicTask" objects.
        For a simple request, you might only need one or two tasks. For a complex request, many more.
        The available TaskTypes are: "create_file", "modify_file", "create_directory".

        **Example Request:** "Create a python script that prints the current time"
        **Example Output:**
        [
          {
            "id": "1",
            "description": "Create a Python file named 'main.py' that imports the datetime library and prints the current time.",
            "type": "create_file",
            "target_files": ["main.py"],
            "prerequisites": [],
            "success_criteria": "The file 'main.py' exists and contains Python code to print the current time.",
            "priority": 1,
            "estimated_complexity": 2
          }
        ]

        Now, analyze the real user request and generate the JSON plan.
        Return ONLY the raw JSON array, with no explanations or markdown.
        """

        user_task = state.get('user_task', '')
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"User Request: {user_task}")]
        
        response = self.llm.invoke(messages)
        response_content = response.content if isinstance(response.content, str) else str(response.content)

        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
        if json_match:
            clean_json_str = json_match.group(1)
        else:
            # If no markdown, assume the whole string is the JSON content
            clean_json_str = response_content

        try:
            tasks_data = json.loads(clean_json_str)
            if not isinstance(tasks_data, list):
                 raise ValueError("JSON response is not a list.")
            atomic_tasks = [
                AtomicTask(
                    id=task_data.get("id", str(uuid.uuid4())),
                    description=task_data.get("description", ""),
                    type=TaskType(task_data.get("type", "create_file")),
                    target_files=task_data.get("target_files", []),
                    prerequisites=task_data.get("prerequisites", []),
                    success_criteria=task_data.get("success_criteria", ""),
                    priority=task_data.get("priority", 5),
                    estimated_complexity=task_data.get("estimated_complexity", 5)
                ) for task_data in tasks_data
            ]
            if not atomic_tasks:
                 raise ValueError("LLM returned an empty list of tasks.")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[DEBUG] Planner failed to parse LLM response ('{e}'). Creating a fallback task.")
            atomic_tasks = [
                AtomicTask(
                    id=str(uuid.uuid4()), description=f"Directly implement the user's request: {user_task}",
                    type=TaskType.CREATE_FILE, target_files=["main.py"], prerequisites=[],
                    success_criteria="The primary request is satisfied.", priority=1, estimated_complexity=5,
                )
            ]

        return {**state, "atomic_tasks": atomic_tasks}

    def create_planner_graph(self):
        workflow = StateGraph(PlannerState)
        workflow.add_node("generate_plan", self.generate_plan)
        workflow.add_edge(START, "generate_plan")
        workflow.add_edge("generate_plan", END)
        return workflow.compile()

def create_planner_service(llm: ChatGoogleGenerativeAI):
    planner = PlannerAgent(llm)
    return planner.create_planner_graph()