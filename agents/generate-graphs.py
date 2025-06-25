# visualize_graphs.py

import os
import sys
from pathlib import Path

import config as app_config
from main import MainOrchestrator

def generate_graphs():
    """
    Initializes the agent orchestrator and saves visualizations of its graphs
    using the dependency-free draw_mermaid_png() method.
    """
    print("Generating graph visualizations...")

    # Define the output directory and create it if it doesn't exist
    output_dir = Path("workflow_graphs")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Graphs will be saved in the '{output_dir.name}' directory.")

    config = app_config.get_workflow_config()

    orchestrator = MainOrchestrator(config)

    # Get the compiled graph objects
    main_graph_app = orchestrator.create_main_graph()
    planner_graph_app = orchestrator.planner_graph
    developer_graph_app = orchestrator.developer_graph

    graphs_to_generate = {
        "overall": main_graph_app,
        "planner": planner_graph_app,
        "developer": developer_graph_app
    }

    try:
        for name, app in graphs_to_generate.items():
            print(f"Generating '{name}' graph...")

            png_bytes = app.get_graph().draw_mermaid_png()

            output_path = output_dir / f"{name}_graph.png"
            with open(output_path, "wb") as f:
                f.write(png_bytes)
            
            print(f"Saved '{name}' graph to {output_path}")

        print("\nAll graphs saved successfully!")

    except Exception as e:
        print(f"\n❌ An error occurred during graph generation.")
        print("This method requires an internet connection to render the graphs.")
        print(f"Error details: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # The config import already checks for the key, but this provides a clearer message.
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable not set.")
        print("Please create a .env file with your key before running the visualization.")
        sys.exit(1)
        
    generate_graphs()