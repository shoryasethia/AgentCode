# usage_example.py

import os
from pathlib import Path
from main import run_development_workflow
from config import get_workflow_config

def simple_example():
    """Simple example of using the workflow"""
    task = "Create a simple ython calculator with basic operations (add, subtract, multiply, divide)"
    workspace = "./my_project"

    Path(workspace).mkdir(exist_ok=True)
    
    print(f"\n🚀 Starting Simple Example: {task}\n")

    result = run_development_workflow(task, workspace, get_workflow_config(workspace))
    
    # Print results
    print(f"\nSuccess: {result['success']}")
    print(f"Summary:\n{result['final_summary']}")
    
    return result

def advanced_example():
    """Advanced example with custom configuration"""

    config = get_workflow_config("./advanced_project")
    config["temperature"] = 0.25
    config["max_iterations"] = 5

    task = """
    Create a 'Random Quote Generator' website. 
    The project must have three separate files: 
    1. `index.html` for the HTML structure.
    2. `style.css` for the styling dark themed.
    3. `script.js` for the functionality.
    The website should display a quote and a button. When the user clicks the button, a new random quote should be displayed.
    """
    
    workspace = "./advanced_project"
    Path(workspace).mkdir(exist_ok=True)
    
    print(f"\n🚀 Starting Advanced Example: Building a Random Quote Generator website...\n")

    # Run workflow with your custom config object
    result = run_development_workflow(task, workspace, config)
    
    # Detailed reporting
    print("=" * 60)
    print("ADVANCED WORKFLOW RESULTS")
    print("=" * 60)
    
    print(f"Task: {task.strip()}")
    print(f"Workspace: {workspace}")
    print(f"Success: {result['success']}")
    
    # Task breakdown
    completed_tasks = result.get('completed_tasks', [])
    print(f"\nCompleted Tasks ({len(completed_tasks)}):")
    if not completed_tasks:
        print("  - None")
    for i, t in enumerate(completed_tasks, 1):
        print(f"{i}. {t['description']}")
        print(f"   Type: {t['type']}")
        print(f"   Files: {', '.join(t['target_files'])}")
    
    # Files summary
    developer_state = result.get('developer_state', {})
    files_created = developer_state.get('files_created', [])
    files_modified = developer_state.get('files_modified', [])
    
    print(f"\nFiles Created ({len(files_created)}):")
    if not files_created:
        print("  - None")
    for file in files_created:
        print(f"  - {file}")
    
    print(f"\nFiles Modified ({len(files_modified)}):")
    if not files_modified:
        print("  - None")
    for file in files_modified:
        print(f"  - {file}")
    
    # Error summary
    errors = developer_state.get('errors_encountered', [])
    if errors:
        print(f"\nErrors Encountered ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\nFinal Summary:\n{result['final_summary']}")
    
    return result


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Please set your GOOGLE_API_KEY environment variable in a .env file")
        print("Create a file named .env and add the line: GOOGLE_API_KEY='your-api-key-here'")
        exit(1)

    print("Workflow Examples using AgentCode [CLI]")
    print("=" * 40)
    print("1. Simple Example")
    print("   -> Task: Create a simple Python calculator app.")
    print("\n2. Advanced Example")
    print("   -> Task: Build a 'Random Quote Generator' website (HTML/CSS/JS).")
    print("\n3. Exit")
    
    choice = input("\nSelect an example (1-3): ").strip()
    
    if choice == "1":
        simple_example()
    elif choice == "2":
        advanced_example()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice. Please run again.")