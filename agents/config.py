# config.py

import os
from typing import Any, Optional
from state import WorkflowConfig, SearchConfig
from dotenv import load_dotenv

load_dotenv()

# Model Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.2))

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables or .env file")

# Workspace Configuration
DEFAULT_WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", "./workspace")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 10))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))


SEARCH_CONFIG: SearchConfig = {
    "internal_enabled": True,
    "external_enabled": True,
    "max_results_per_query": int(os.getenv("MAX_SEARCH_RESULTS", 10)),
    "relevance_threshold": float(os.getenv("RELEVANCE_THRESHOLD", 0.5)),
    "search_timeout": int(os.getenv("SEARCH_TIMEOUT", 30))
}

# Logging Configuration
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")


def get_workflow_config(workspace_path: Optional[str] = None) -> WorkflowConfig:
    """Get complete workflow configuration dictionary."""
    config: WorkflowConfig = {
        "model_name": GEMINI_MODEL,
        "temperature": TEMPERATURE,
        "max_iterations": MAX_ITERATIONS,
        "workspace_path": workspace_path or DEFAULT_WORKSPACE_PATH,
        "search_config": SEARCH_CONFIG,
        "logging_level": LOGGING_LEVEL,
        "max_retries": MAX_RETRIES
    }
    return config