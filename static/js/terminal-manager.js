// Path: js/terminal-manager.js

/**
 * TerminalManager - Handles terminal output display and management
 */
class TerminalManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null; // Will be initialized in initialize()
        this.maxLines = 1000; // Maximum items (lines or images) to keep in terminal history
        this.history = []; // Stores {text, type, timestamp} or {type: 'image', src, timestamp, alt}
    }

    /**
     * Initialize terminal
     * Ensures the DOM container is available.
     */
    initialize() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            // This should ideally not happen if HTML is correct.
            console.error(`Terminal container with id '${this.containerId}' not found. Attempting to create a fallback (not recommended).`);
            // Fallback: Create a div and append it to the body or a specific parent.
            // For a real application, ensure the HTML element exists.
            // this.container = document.createElement('div');
            // this.container.id = this.containerId;
            // document.body.appendChild(this.container); // Or a more specific parent
            throw new Error(`Terminal container with id '${this.containerId}' not found in the DOM.`);
        }
        // Initial messages like "AgentCode Terminal" are good in index.html or can be added by app.js
        // For example, app.js could call:
        // this.writeLine('AgentCode Terminal Initialized.');
        // this.writeLine('Ready to execute code...');
        // this.writeLine('');
    }

    /**
     * Helper to ensure the container is initialized.
     * @returns {boolean} True if the container is available, false otherwise.
     */
    _ensureContainer() {
        if (!this.container) {
            try {
                this.initialize();
            } catch (e) {
                console.error("Failed to ensure terminal container:", e);
                return false;
            }
        }
        return !!this.container;
    }

    /**
     * Write a text line to the terminal.
     * @param {string} text - The text to write.
     * @param {string} [type='normal'] - The type of the line (e.g., 'output', 'error', 'success').
     */
    writeLine(text, type = 'normal') {
        if (!this._ensureContainer()) return;

        const timestamp = new Date().toLocaleTimeString();
        const lineEntry = { text: String(text), type, timestamp }; // Ensure text is a string
        
        this.history.push(lineEntry);
        this._appendToTerminalDOM(lineEntry.text, lineEntry.type);
        this._limitHistory();
        this._scrollToBottom();
    }

    /**
     * Write an image to the terminal (e.g., for plots).
     * @param {string} base64DataUri - The base64 encoded image data URI.
     * @param {string} [altText='Generated Output'] - Alt text for the image.
     */
    writeImage(base64DataUri, altText = "Generated Plot") {
        if (!this._ensureContainer()) return;

        const timestamp = new Date().toLocaleTimeString();
        const imageEntry = { type: 'image', src: base64DataUri, alt: altText, timestamp };
        this.history.push(imageEntry);

        const imgElement = document.createElement('img');
        imgElement.src = imageEntry.src;
        imgElement.alt = imageEntry.alt;
        // Apply some basic styling for the image in the terminal
        imgElement.style.maxWidth = '90%'; // Responsive width within terminal
        imgElement.style.maxHeight = '400px'; // Prevent overly tall images
        imgElement.style.display = 'block';    // For centering and margins
        imgElement.style.margin = '10px auto'; // Center with vertical spacing
        imgElement.style.border = '1px solid var(--border-color)';
        imgElement.style.padding = '3px';
        imgElement.style.backgroundColor = 'var(--bg-primary)'; // Match background if image has transparency

        // Wrap image in a div for consistent handling with _limitHistory
        const wrapper = document.createElement('div');
        wrapper.appendChild(imgElement);
        this.container.appendChild(wrapper);
        
        this._limitHistory();
        this._scrollToBottom();
    }

    /**
     * Appends a text line to the terminal's DOM structure.
     * @param {string} text - The text content of the line.
     * @param {string} type - The type of the line, for styling.
     */
    _appendToTerminalDOM(text, type) {
        if (!this.container) return;

        const element = document.createElement('span');
        element.textContent = text + '\n';
        
        // Apply styling based on line type using CSS variables for colors
        switch (type) {
            case 'command': // Though commands are not printed by default anymore
                element.style.color = 'var(--accent-blue)';
                element.style.fontWeight = 'bold';
                break;
            case 'output':
                element.style.color = 'var(--text-primary)';
                break;
            case 'error':
                element.style.color = 'var(--accent-red)';
                break;
            case 'success':
                element.style.color = 'var(--accent-green)';
                break;
            case 'warning':
                element.style.color = 'var(--accent-yellow)';
                break;
            case 'info': // Added an info type
                element.style.color = 'var(--accent-blue)'; // Or a dedicated info color
                break;
            default: // 'normal' or any other
                element.style.color = 'var(--text-secondary)';
        }
        this.container.appendChild(element);
    }
    
    /**
     * Write multiple text lines to the terminal.
     * @param {string[]} lines - An array of strings to write.
     * @param {string} [type='normal'] - The type for these lines.
     */
    writeLines(lines, type = 'normal') {
        if (!Array.isArray(lines)) lines = [lines]; // Handle single string input
        lines.forEach(line => {
            const textLine = String(line); // Ensure it's a string
            if (textLine.trim()) { // Only write non-empty trimmed lines
                this.writeLine(textLine, type);
            }
        });
    }

    /**
     * Write execution result to terminal (stdout, stderr, errors).
     * @param {null} code - This parameter is no longer used to print code, pass null.
     * @param {object} result - The result object from Pyodide execution.
     *                           Expected: { success: boolean, stdout?: string, stderr?: string, error?: string }
     */
    writeExecutionResult(code, result) { // 'code' param kept for signature compatibility if needed, but not used.
        if (!this._ensureContainer()) return;

        if (!result) {
            this.writeLine('Error: No result returned from execution.', 'error');
            return;
        }

        // Write stdout if present and not empty
        if (result.stdout && String(result.stdout).trim()) {
            String(result.stdout).trim().split('\n').forEach(line => {
                this.writeLine(line, 'output');
            });
        }

        // Write stderr if present and not empty
        if (result.stderr && String(result.stderr).trim()) {
            String(result.stderr).trim().split('\n').forEach(line => {
                this.writeLine(line, 'error');
            });
        }

        // Write primary error message if execution failed and error message exists
        // and it's not already fully covered by stderr (to avoid duplicate full tracebacks)
        if (!result.success && result.error) {
            const errorStr = String(result.error);
            if (!result.stderr || !String(result.stderr).includes(errorStr.split('\n')[0])) { // Check if first line of error is in stderr
                 this.writeLine(`Error: ${errorStr}`, 'error');
            }
        }
        this.writeLine(''); // Add an empty line for better readability after execution block
    }

    /**
     * Write package installation result.
     * @param {string} packageName - The name of the package.
     * @param {object} result - Result object: { success: boolean, message: string }
     */
    writePackageResult(packageName, result) {
        if (!this._ensureContainer()) return;
        if (result.success) {
            this.writeLine(`📦 ${result.message}`, 'success');
        } else {
            this.writeLine(`❌ ${result.message}`, 'error');
        }
        this.writeLine(''); // Spacing
    }

    /**
     * Clear terminal display and history.
     */
    clear() {
        if (this._ensureContainer()) {
            this.container.innerHTML = '';
        }
        this.history = [];
    }

    /**
     * Get terminal history (array of line/image objects).
     * @returns {object[]} A copy of the history array.
     */
    getHistory() {
        return [...this.history]; // Return a shallow copy
    }

    /**
     * Export terminal content as a single text string.
     * @returns {string} Text representation of the terminal history.
     */
    exportAsText() {
        return this.history.map(entry => {
            if (entry.type === 'image') {
                return `[${entry.timestamp}] [Image Displayed: ${entry.alt || 'Plot'}]`;
            }
            return `[${entry.timestamp}] ${entry.text}`;
        }).join('\n');
    }

    /**
     * Limit terminal history (both internal array and DOM) to prevent memory issues.
     */
    _limitHistory() {
        if (!this.container) return;

        while (this.history.length > this.maxLines) {
            this.history.shift(); // Remove from the beginning of the history array
            if (this.container.firstChild) {
                this.container.removeChild(this.container.firstChild); // Remove corresponding DOM element
            }
        }
    }

    /**
     * Scroll terminal to the bottom.
     */
    _scrollToBottom() {
        if (this.container) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    /**
     * Set terminal theme (mostly handled by CSS variables on body/container).
     * This function could be used for theme-specific JS logic if needed in the future.
     * @param {string} theme - 'dark' or 'light'.
     */
    setTheme(theme) {
        if (!this._ensureContainer()) return;
    }
}