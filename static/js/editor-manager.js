// Path: js/editor-manager.js

/**
 * EditorManager - Handles Monaco Editor initialization and management
 */
class EditorManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.editor = null;
        this.isReady = false;
        this.defaultCode = `# Write your Python code here and click Run

print("Hello, World!")


x = 10
y = 20
result = x + y
print(f"The sum of {x} and {y} is {result}")

# Example: Working with lists
numbers = [1, 2, 3, 4, 5]
squared = [n**2 for n in numbers]
print(f"Original: {numbers}")
print(f"Squared: {squared}")
`;
        this.localStorageKey = 'agentcode-editor-content';
        this.saveTimeout = null;
        this.saveDelay = 1000; // ms, delay after user stops typing
    }

    /**
     * Initialize Monaco Editor
     */
    async initialize() {
        return new Promise((resolve, reject) => {
            require.config({ 
                paths: { 
                    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' 
                } 
            });

            require(['vs/editor/editor.main'], () => {
                try {
                    const savedCode = this.loadCodeFromStorage();
                    this.editor = monaco.editor.create(
                        document.getElementById(this.containerId), 
                        {
                            value: savedCode !== null ? savedCode : this.defaultCode, // Load saved code or default
                            language: 'python',
                            theme: 'vs-dark', // Initial theme, app.js will update it
                            automaticLayout: true,
                            minimap: { enabled: false },
                            fontSize: 14,
                            lineNumbers: 'on',
                            roundedSelection: false,
                            scrollBeyondLastLine: false,
                            readOnly: false,
                            cursorStyle: 'line',
                            wordWrap: 'on',
                            folding: true,
                            lineNumbersMinChars: 3,
                            scrollbar: {
                                vertical: 'auto',
                                horizontal: 'auto'
                            }
                        }
                    );

                    this.setupKeyboardShortcuts();
                    this.setupAutoSave(); // Setup auto-saving mechanism
                    
                    this.isReady = true;
                    resolve(this.editor);
                } catch (error) {
                    console.error("Monaco Editor initialization failed:", error);
                    reject(error);
                }
            });
        });
    }

    /**
     * Setup auto-saving mechanism
     */
    setupAutoSave() {
        if (!this.editor) return;

        this.editor.onDidChangeModelContent(() => {
            if (this.saveTimeout) {
                clearTimeout(this.saveTimeout);
            }
            this.saveTimeout = setTimeout(() => {
                this.saveCodeToStorage();
            }, this.saveDelay);
        });

        // Save when the window is about to be unloaded (refresh/close)
        window.addEventListener('beforeunload', () => {
            this.saveCodeToStorage(true); // Force immediate save
        });
    }

    /**
     * Save current code to localStorage
     */
    saveCodeToStorage(immediate = false) {
        if (this.editor) {
            const currentCode = this.editor.getValue();
            try {
                localStorage.setItem(this.localStorageKey, currentCode);
                // console.log('Code ' + (immediate ? 'force-' : 'auto-') + 'saved to localStorage.');
            } catch (e) {
                console.error('Failed to save code to localStorage:', e);
                if (window.pythonIDE && window.pythonIDE.notificationManager) {
                    window.pythonIDE.notificationManager.warning('Auto-Save Failed', 'Could not save code. Browser storage might be full.', 8000);
                }
            }
        }
        if (immediate && this.saveTimeout) { // Clear pending timeout if forcing save
             clearTimeout(this.saveTimeout);
        }
    }

    /**
     * Load code from localStorage
     */
    loadCodeFromStorage() {
        try {
            const savedCode = localStorage.getItem(this.localStorageKey);
            // if (savedCode !== null) console.log('Code loaded from localStorage.');
            return savedCode; // Can be null if not found
        } catch (e) {
            console.error('Failed to load code from localStorage:', e);
        }
        return null;
    }

    getCode() {
        return this.editor ? this.editor.getValue() : '';
    }

    setCode(code) {
        if (this.editor) {
            this.editor.setValue(code);
            this.saveCodeToStorage(true); // Also save when code is set programmatically
        }
    }

    clear() {
        if (this.editor) {
            this.editor.setValue('');
            this.saveCodeToStorage(true); // Save empty state
        }
    }

    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    }

    getSelectedText() {
        if (!this.editor) return '';
        const selection = this.editor.getSelection();
        return this.editor.getModel().getValueInRange(selection);
    }

    insertText(text) {
        if (!this.editor) return;
        const position = this.editor.getPosition();
        this.editor.executeEdits('insert-text', [{
            range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column),
            text: text
        }]);
        // onDidChangeModelContent will trigger auto-save
    }

    setTheme(theme) {
        if (this.editor && monaco.editor) { // Check monaco.editor for safety
            monaco.editor.setTheme(theme);
        }
    }

    resize() {
        if (this.editor) {
            this.editor.layout();
        }
    }

    setupKeyboardShortcuts() {
        if (!this.editor) return;
        this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
            const event = new CustomEvent('runCode');
            document.dispatchEvent(event);
        });
        this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Slash, () => {
            this.editor.trigger('keyboard', 'editor.action.commentLine', {});
        });
    }
    
    dispose() {
        if (this.saveTimeout) { // Clear any pending save operation
            clearTimeout(this.saveTimeout);
        }
        window.removeEventListener('beforeunload', () => this.saveCodeToStorage(true)); // Clean up listener

        if (this.editor) {
            this.editor.dispose();
            this.editor = null;
            this.isReady = false;
        }
    }
}