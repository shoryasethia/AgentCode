# 🚀 AgentCode – An Agentic Web-Based IDE

**AgentCode** is a modern coding IDE that combines AI agents and a sleek web interface to help you build projects through natural language conversations.

---

## ✨ Features

* 💡 **AI-Powered Development**: Chat with AI to generate, modify, and refactor code
* 🧠 **Multi-Agent System**: Planner & Developer agents break down and solve complex tasks
* 🖥️ **Modern IDE Interface**: React + Monaco Editor + Pyodide to run Python scripts
* 🔒 **Secure Authentication**: User login with session management
* 🗂️ **Workspace Management**: Isolated workspaces for each user
* 💬 **Real-time Chat**: Interact conversationally with AI agents

> For technical details refer [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)
---

## ⚙️ Quick Start

### ✅ Prerequisites

* Python **3.10+**
* Node.js **18+**
* Google **Gemini API Key**

### 📦 Installation

```bash
# 1. Clone the repository
git clone https://github.com/shoryasethia/agentcode.git
cd agentcode

# 2. Set up Python environment
python -m venv myenv
# Activate:
# Windows:
myenv\Scripts\activate
# Linux/Mac:
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 🔐 Configure Environment

```bash
# Create a .env file with your Gemini API key
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### 🌐 Set Up Frontend

```bash
cd frontend
npm install
```

---

## ▶️ Running the Application

You need to run **three servers**:

### 🛠️ Option 1: Manual (3 Terminals)

1. **Authentication Server** (Flask)

   ```bash
   python app.py
   ```

2. **AI Agent Server** (FastAPI)

   ```bash
   uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Frontend Server** (React)

   ```bash
   cd frontend
   npm run dev
   ```

### 🪟 Option 2: Batch Script (Windows Only)

```bash
start-servers.bat
```

---

## 🌍 Access the Application

* **Frontend**: [http://localhost:3000](http://localhost:3000)
* **API Server**: [http://localhost:8000](http://localhost:8000)
* **Auth Server**: [http://localhost:5000](http://localhost:5000)

---

## 💡 Usage Guide

1. **Register** a new account or login
2. **Chat** with the AI about your project
3. **Review** code suggestions and apply changes
4. **Iterate** and build faster

### 🗣️ Example Prompts

* *“Create a React todo list component”*
* *“Build a Flask API for user management”*
* *“Add error handling to this function”*
* *“Refactor this to use TypeScript”*

---

## 🏗️ Project Structure

```bash
agentcode/
├── frontend/              # React + Vite frontend
│   ├── src/
│   │   ├── components/    # React UI components
│   │   └── services/      # API integration
│   └── package.json
├── agents/                # AI agent system
│   ├── planner/           # Task planning agent
│   ├── developer/         # Code generation agent
│   └── search/            # Agent search functions
├── workspaces/            # User project files (auto-generated)
├── instance/              # SQLite database (auto-created)
├── app.py                 # Flask Auth server
├── api_server.py          # FastAPI AI server
├── database.py            # DB setup and utilities
├── logger.py              # App logging system
└── requirements.txt       # Python dependencies
```

---

## 🔧 Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 🗃️ Database

* Uses **SQLite**, automatically created inside the `instance/` directory.
* No manual setup required.

---

## 🛠️ Development Notes

* **Frontend**: Add or modify components in `frontend/src/components/`
* **Backend**: Update APIs in `api_server.py`
* **Agents**: Adjust logic in the `agents/` subfolders

---

### 📜 View Logs

```bash
python view_logs.py --limit 20
```

👉 For more details, refer to [**LOGGING.md**](LOGGING.md)

---

## 🔐 Security Features

* Encrypted password hashing
* Session-based authentication
* Workspace isolation
* CORS enabled
* Full logging for activity tracking

---

## 📝 License

Apache License – see the [LICENSE](LICENSE) file for full details.

---

## 📞 Support

Found a bug or have a question?
👉 [Open an issue on GitHub](https://github.com/shoryasethia/agentcode/issues)

