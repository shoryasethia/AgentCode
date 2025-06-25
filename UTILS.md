> Before using matplotlib before it also add `enable_ide_plotting()`

> `ctrl+shit+R` hard reset
You've got the core idea exactly right! Here's a breakdown of how you would implement this "send code to agent for processing and update editor" workflow, integrating with your existing structure.

**Conceptual Workflow:**

1.  **User Interaction:**
    *   The user writes code in the Monaco editor.
    *   The user types a prompt (e.g., "Refactor this code to be more efficient," "Add error handling," "Explain this function") into a new input field you'll add to the UI.
    *   The user clicks a new button (e.g., "Process with Agent," "Refine Code").

2.  **Frontend (JavaScript - `app.js`):**
    *   **`onClick` Handler:** The new button's click event triggers a JavaScript function.
    *   **Gather Data:**
        *   Get the current code from the editor: `this.editorManager.getCode()`.
        *   Get the prompt from the new input field: `document.getElementById('agentPromptInput').value`.
    *   **Format for Agent:** Combine the prompt and code into a single string as your Python agent expects: `system_prompt_for_agent = user_prompt_text + "\n\n# Code:\n" + current_code_string;` (The exact formatting depends on how your Python agent parses this combined input).
    *   **Make API Call (POST Request):**
        *   Use `fetch` to send a POST request to your backend API endpoint that hosts the Python agent.
        *   The body of the request will contain the `system_prompt_for_agent` string (likely as JSON).
        *   Example: `{'inputText': system_prompt_for_agent}`.
    *   **Handle Response:**
        *   When the backend responds (after the agent processes the input), the frontend receives the agent's output (which should be the modified code string).
        *   **Update Editor:** Use `this.editorManager.setCode(new_code_from_agent);` to replace the content of the Monaco editor with the agent's refined code.
        *   **Provide Feedback:** Show a toast notification (e.g., "Code processed by agent successfully!" or an error message if the API call failed).

3.  **Backend (Python - Your Agent):**
    *   **API Endpoint:** A web framework (like Flask, FastAPI, Django) exposes an endpoint (e.g., `/process-code-with-agent`).
    *   **Receive Request:** The endpoint receives the POST request with the combined prompt and code string.
    *   **Invoke Agent:** Pass this string to your Python agent function/class.
    *   **Agent Processing:** Your agent does its magic (editing, refining, etc.).
    *   **Return Result:** The agent returns the modified code string.
    *   **Send Response:** The API endpoint sends this modified code string back to the frontend in the HTTP response (e.g., as JSON: `{'processedCode': modified_code_string}`).

**Implementation Steps (Frontend - `app.js` and `index.html`):**

**1. Add UI Elements in `index.html`:**

You'll need an input field for the user's prompt and a button to trigger the agent. A good place might be in the `header` or near the `editor-section`.

```html
<!-- index.html -->

<!-- Inside the <header class="header"> <div class="controls"> -->
<div class="controls">
    <button id="runBtn" class="btn btn-primary" disabled>Run Code</button>
    <button id="clearBtn" class="btn btn-secondary">Clear Output</button>
    <button id="installBtn" class="btn btn-tertiary" disabled>Install Packages</button>
    <button id="downloadBtn" class="btn btn-secondary">Download</button>
    <button id="themeBtn" class="btn btn-secondary">🌙 Light</button>
    
    <!-- NEW AGENT CONTROLS -->
    <input type="text" id="agentPromptInput" placeholder="Enter prompt for AI agent..." style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary); flex-grow: 1; min-width: 200px;">
    <button id="agentProcessBtn" class="btn btn-primary">✨ Process with Agent</button> 
    <!-- You can choose a different button style, e.g., btn-secondary or a new custom one -->
</div>
```
*   Added an `input` with `id="agentPromptInput"`.
*   Added a `button` with `id="agentProcessBtn"`.
*   Basic inline styling for the input for now; you can move this to `styles.css`.

**2. Update `app.js`:**

```javascript
// Path: js/app.js

class PythonIDE {
    constructor() {
        // ... (existing constructor code) ...
        this.pyodideManager.setDisplayPlotCallback(
            this.terminalManager.writeImage.bind(this.terminalManager)
        );
        
        this.elements = {
            // ... (existing elements) ...
            status: document.getElementById('status'),
            runBtn: document.getElementById('runBtn'),
            // ...
            mainContent: document.querySelector('.main-content'), // Used for resizer width calculations

            // NEW AGENT ELEMENTS
            agentPromptInput: document.getElementById('agentPromptInput'),
            agentProcessBtn: document.getElementById('agentProcessBtn')
        };
        // ... (rest of constructor) ...
    }

    // ... (existing methods like initialize, initializeComponents) ...

    setupEventListeners() {
        // ... (existing event listeners) ...
        this.elements.runBtn.addEventListener('click', () => this.executeCode());
        // ...

        // NEW AGENT BUTTON LISTENER
        if (this.elements.agentProcessBtn && this.elements.agentPromptInput) {
            this.elements.agentProcessBtn.addEventListener('click', () => this.processCodeWithAgent());
        } else {
            console.warn("Agent processing UI elements not found.");
        }
    }

    // ... (existing methods like initResizer, themes, executeCode, etc.) ...

    /**
     * Gathers code and prompt, sends to backend agent, and updates editor with response.
     */
    async processCodeWithAgent() {
        if (!this.isInitialized) {
            this.showNotification('Not Ready', 'IDE is still initializing.', 'warning');
            return;
        }

        const currentCode = this.editorManager.getCode();
        const userPrompt = this.elements.agentPromptInput.value.trim();

        if (!userPrompt) {
            this.showNotification('Input Required', 'Please enter a prompt for the agent.', 'warning');
            this.elements.agentPromptInput.focus();
            return;
        }

        // Optional: Check if there's code if your agent requires it
        // if (!currentCode.trim() && agent_requires_code) {
        //     this.showNotification('No Code', 'Please write some code for the agent to process.', 'warning');
        //     return;
        // }

        // Format the input for your backend agent
        // Example: combining prompt and code. Adjust as per your agent's needs.
        const agentInputText = `${userPrompt}\n\n--- CODE START ---\n${currentCode}\n--- CODE END ---`;
        
        this.updateStatus('Agent Processing...', 'loading');
        this.elements.agentProcessBtn.disabled = true;
        this.elements.agentProcessBtn.textContent = 'Processing...';
        this.showNotification('Agent', 'Sending to agent for processing...', 'info', 3000);


        try {
            // Replace '/api/process-with-agent' with your actual backend endpoint
            const response = await fetch('/api/process-with-agent', { // <<< YOUR BACKEND ENDPOINT
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ inputText: agentInputText }), // Or whatever structure your agent expects
            });

            if (!response.ok) {
                // Handle HTTP errors (e.g., 404, 500)
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(`Agent API Error: ${response.status} - ${errorData.message || 'Unknown error'}`);
            }

            const result = await response.json();

            if (result && typeof result.processedCode === 'string') {
                // Update the Monaco editor with the processed code
                this.editorManager.setCode(result.processedCode);
                this.showNotification('Agent Success', 'Code processed and updated!', 'success');
                this.elements.agentPromptInput.value = ""; // Clear prompt after successful processing
            } else {
                throw new Error('Agent returned an invalid response format.');
            }

        } catch (error) {
            console.error('Error processing with agent:', error);
            this.showNotification('Agent Error', `Failed: ${error.message}`, 'error', 8000);
        } finally {
            this.updateStatus('Ready', 'ready');
            this.elements.agentProcessBtn.disabled = false;
            this.elements.agentProcessBtn.textContent = '✨ Process with Agent';
        }
    }

    // ... (rest of your app.js methods) ...
}

// ... (DOMContentLoaded listener) ...
```

**Explanation of `app.js` Changes:**

1.  **`constructor`:** Added `agentPromptInput` and `agentProcessBtn` to `this.elements`.
2.  **`setupEventListeners`:** Added an event listener for the new `agentProcessBtn`.
3.  **`processCodeWithAgent()` method (New):**
    *   Gets the code from `this.editorManager.getCode()`.
    *   Gets the prompt from `this.elements.agentPromptInput.value`.
    *   Constructs `agentInputText` (you'll need to match the exact format your Python agent expects if it's parsing this combined string).
    *   **`fetch('/api/process-with-agent', ...)`:** This is the crucial part.
        *   **Replace `/api/process-with-agent` with the actual URL of your backend endpoint** where your Python agent code is running.
        *   It sends a `POST` request.
        *   The `body` is a JSON string. Here, it's `{'inputText': agentInputText}`. Your backend will parse this JSON to get the `inputText`.
    *   **Response Handling:**
        *   It checks if `response.ok` (status code 200-299).
        *   It parses the JSON response from the backend. It expects the backend to return JSON like `{'processedCode': 'the_new_code_string'}`.
        *   **`this.editorManager.setCode(result.processedCode);`**: This is where the Monaco editor's content is updated with the agent's output.
    *   **Error Handling:** Basic error handling for network issues or non-OK HTTP responses.
    *   **UI Feedback:** Updates the status bar, disables/enables the button, and shows toast notifications.

**Regarding your backend Python agent:**

*   It needs to be running on a server (e.g., using Flask, FastAPI).
*   It needs an API endpoint that accepts POST requests (e.g., `/api/process-with-agent`).
*   This endpoint will receive the JSON payload (e.g., `{'inputText': "prompt_and_code_string"}`).
*   It will then call your agent logic with `inputText`.
*   Your agent logic processes this string and returns the modified code string.
*   The endpoint then sends back a JSON response like `{'processedCode': 'modified_code_string'}`.

This provides a solid framework. You'll need to implement the backend part and ensure the data structures for request/response match between frontend and backend.