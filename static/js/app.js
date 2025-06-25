// Path: js/app.js
class PythonIDE {
    constructor() {
        this.terminalManager = new TerminalManager('terminalContent');
        this.pyodideManager = new PyodideManager();
        this.editorManager = new EditorManager('editor');
        this.notificationManager = new NotificationManager();

        this.pyodideManager.setDisplayPlotCallback(
            this.terminalManager.writeImage.bind(this.terminalManager)
        );
        
        this.elements = {
            status: document.getElementById('status'),
            runBtn: document.getElementById('runBtn'),
            clearBtn: document.getElementById('clearBtn'),
            installBtn: document.getElementById('installBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            themeBtn: document.getElementById('themeBtn'),
            packageModal: document.getElementById('packageModal'),
            packageInput: document.getElementById('packageInput'),
            confirmInstall: document.getElementById('confirmInstall'),
            closeModal: document.querySelector('#packageModal .close'),
            downloadModal: document.getElementById('downloadModal'),
            filenameInput: document.getElementById('filenameInput'),
            confirmDownload: document.getElementById('confirmDownload'),
            closeDownload: document.querySelector('#downloadModal .close-download'),
            resizer: document.getElementById('resizer'),
            editorSection: document.querySelector('.editor-section'),
            terminalSection: document.querySelector('.terminal-section'),
            mainContent: document.querySelector('.main-content')
        };
        this.isInitialized = false;
        this.isDarkTheme = this._getInitialThemePreference();
        this.executionCount = 0;
        this.lastExecutionTime = null;
    }

    _getInitialThemePreference() {
        const savedTheme = localStorage.getItem('agentcode-theme');
        if (savedTheme) return savedTheme === 'dark';
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) return false;
        return true;
    }

    async initialize() {
        try {
            this.updateStatus('Initializing IDE...', 'loading');
            // No direct terminal log for initialization start

            await this.initializeComponents();
            this.setupEventListeners();
            this.applyInitialTheme();

            this.isInitialized = true;
            this.updateStatus('Ready', 'ready');
            this.showNotification('Ready', 'AgentCode IDE is ready!', 'success', 3000);
            
        } catch (error) {
            console.error('Failed to initialize IDE:', error);
            this.updateStatus('Initialization Failed!', 'error');
            if (this.terminalManager && this.terminalManager._ensureContainer()) {
                 this.terminalManager.writeLine(`❌ CRITICAL IDE Initialization Error: ${error.message}`, 'error');
            }
            this.showNotification('IDE Error', `Failed to initialize: ${error.message}`, 'error', 0);
        }
    }

    async initializeComponents() {
        try {
            this.terminalManager.initialize(); 

            this.updateStatus('Loading Editor...', 'loading');
            await this.editorManager.initialize();
            if (this.editorManager.getCode() !== this.editorManager.defaultCode && localStorage.getItem(this.editorManager.localStorageKey) !== null) {
                 this.showNotification('Code Restored', 'Previous code loaded.', 'info', 3000);
            }
            
            this.updateStatus('Loading Python Runtime...', 'loading');
            await this.pyodideManager.initialize();
            
            this.elements.runBtn.disabled = false;
            this.elements.installBtn.disabled = false;
        } catch (error) {
            console.error("Component initialization failed:", error);
            if (this.terminalManager && this.terminalManager._ensureContainer()) {
                 this.terminalManager.writeLine(`❌ Component Init Error: ${error.message}`, 'error');
            }
            throw new Error(`Component initialization failed: ${error.message}`);
        }
    }

    setupEventListeners() {
        this.elements.runBtn.addEventListener('click', () => this.executeCode());
        this.elements.clearBtn.addEventListener('click', () => this.clearTerminal());
        this.elements.installBtn.addEventListener('click', () => this.showPackageModal());
        this.elements.downloadBtn.addEventListener('click', () => this.showDownloadModal());
        this.elements.themeBtn.addEventListener('click', () => this.toggleTheme());
        this.elements.closeModal?.addEventListener('click', () => this.hidePackageModal());
        this.elements.confirmInstall.addEventListener('click', () => this.installPackages());
        this.elements.closeDownload?.addEventListener('click', () => this.hideDownloadModal());
        this.elements.confirmDownload.addEventListener('click', () => this.downloadCode());
        this.elements.packageModal.addEventListener('click', (e) => { if (e.target === this.elements.packageModal) this.hidePackageModal(); });
        this.elements.downloadModal.addEventListener('click', (e) => { if (e.target === this.elements.downloadModal) this.hideDownloadModal(); });
        this.elements.packageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.installPackages(); }});
        this.elements.filenameInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') { e.preventDefault(); this.downloadCode(); }});
        document.addEventListener('runCode', () => this.executeCode());
        window.addEventListener('resize', () => { if (this.editorManager.isReady) this.editorManager.resize(); });
        document.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); this.showDownloadModal(); }});
        document.querySelectorAll('.btn').forEach(btn => btn.addEventListener('contextmenu', (e) => e.preventDefault()));
        if (this.elements.resizer && this.elements.editorSection && this.elements.terminalSection && this.elements.mainContent) { this.initResizer(); }
        else { console.warn("Resizer elements not found."); }
    }

    initResizer() {
        const resizer = this.elements.resizer;
        const editorSection = this.elements.editorSection;
        const terminalSection = this.elements.terminalSection;
        const mainContent = this.elements.mainContent;
        let isResizing = false;
        const minPanelWidthPx = 150;
        const loadPanelSizes = () => {
            const editorBasis = localStorage.getItem('agentcode-editor-flex-basis');
            const terminalBasis = localStorage.getItem('agentcode-terminal-flex-basis');
            if (editorBasis && terminalBasis) {
                editorSection.style.flexBasis = editorBasis;
                terminalSection.style.flexBasis = terminalBasis;
                if (this.editorManager.isReady) this.editorManager.resize();
            }
        };
        loadPanelSizes();
        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault(); isResizing = true; resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
        const handleMouseMove = (e) => {
            if (!isResizing) return;
            const containerRect = mainContent.getBoundingClientRect();
            let newEditorWidth = e.clientX - containerRect.left - (resizer.offsetWidth / 2);
            newEditorWidth = Math.max(minPanelWidthPx, newEditorWidth);
            newEditorWidth = Math.min(newEditorWidth, containerRect.width - minPanelWidthPx - resizer.offsetWidth);
            const editorPercentage = (newEditorWidth / containerRect.width) * 100;
            const resizerPercentage = (resizer.offsetWidth / containerRect.width) * 100;
            const terminalPercentage = 100 - editorPercentage - resizerPercentage;
            editorSection.style.flexBasis = `${editorPercentage}%`;
            terminalSection.style.flexBasis = `${terminalPercentage}%`;
            if (this.editorManager.isReady) this.editorManager.resize();
        };
        const handleMouseUp = () => {
            if (!isResizing) return;
            isResizing = false; resizer.classList.remove('active');
            document.body.style.cursor = 'default';
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            localStorage.setItem('agentcode-editor-flex-basis', editorSection.style.flexBasis);
            localStorage.setItem('agentcode-terminal-flex-basis', terminalSection.style.flexBasis);
        };
    }

    applyInitialTheme() { this.updateThemeDOMProperties(); }
    toggleTheme() {
        this.isDarkTheme = !this.isDarkTheme;
        this.updateThemeDOMProperties();
        localStorage.setItem('agentcode-theme', this.isDarkTheme ? 'dark' : 'light');
        this.showNotification('Theme Switched', `Using ${this.isDarkTheme ? 'Dark' : 'Light'} theme.`, 'info', 2000);
    }
    updateThemeDOMProperties() {
        const monacoTheme = this.isDarkTheme ? 'vs-dark' : 'vs';
        if (this.editorManager.isReady) this.editorManager.setTheme(monacoTheme);
        this.elements.themeBtn.textContent = this.isDarkTheme ? '☀️ Light' : '🌙 Dark';
        if (this.isDarkTheme) document.body.removeAttribute('data-theme');
        else document.body.setAttribute('data-theme', 'light');
    }

    async executeCode() {
        if (!this.isInitialized) {
            this.showNotification('Not Ready', 'IDE still initializing.', 'warning'); return;
        }
        const code = this.editorManager.getCode().trim();
        if (!code) {
            this.showNotification('No Code', 'Editor is empty.', 'warning'); return;
        }

        try {
            this.updateStatus('Executing...', 'loading');
            this.elements.runBtn.disabled = true; this.elements.runBtn.textContent = 'Running...';
            const startTime = performance.now();
            const result = await this.pyodideManager.executeCode(code);
            const endTime = performance.now();
            const executionTime = (endTime - startTime).toFixed(2);
            this.executionCount++; this.lastExecutionTime = executionTime;
            
            this.terminalManager.writeExecutionResult(null, result); 
            
            if (result.success) {
                this.showNotification('Success', `Executed in ${executionTime}ms.`, 'success', 3000);
            } else {
                this.showNotification('Execution Error', `Failed. See terminal for details.`, 'error');
            }
        } catch (error) { 
            console.error("JS Error during code execution:", error); 
            this.showNotification('Script Error', `Execution failed: ${error.message}`, 'error');
        } finally {
            this.updateStatus('Ready', 'ready');
            this.elements.runBtn.disabled = false; this.elements.runBtn.textContent = 'Run Code';
        }
    }

    clearTerminal() {
        const historyLength = this.terminalManager.getHistory().length;
        if (historyLength > 50 && !confirm(`Clear ${historyLength} terminal items?`)) return;
        this.terminalManager.clear();
        this.showNotification('Terminal Cleared', 'Output cleared.', 'info', 2000);
    }

    showPackageModal() {
        this.elements.packageModal.style.display = 'block';
        this.elements.packageInput.focus();
        if (!this.elements.packageInput.value.trim()) {
            this.elements.packageInput.value = ['pip install numpy', 'pip install pandas matplotlib', 'pip install requests'].join('\n');
        }
        const textarea = this.elements.packageInput;
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }
    hidePackageModal() { this.elements.packageModal.style.display = 'none'; }
    showDownloadModal() { 
        this.elements.downloadModal.style.display = 'block';
        this.elements.filenameInput.focus(); this.elements.filenameInput.select();
    }
    hideDownloadModal() { this.elements.downloadModal.style.display = 'none'; }

    async installPackages() {
        const commands = this.elements.packageInput.value.trim();
        if (!commands) {
            this.showNotification('No Packages', 'Enter package commands.', 'warning'); return;
        }
        this.elements.confirmInstall.disabled = true; this.elements.confirmInstall.textContent = 'Installing...';
        this.showNotification('Packages', 'Attempting to install...', 'info', 2000);

        try {
            const results = await this.pyodideManager.installFromPipCommands(commands);
            let successCount = 0, failCount = 0;
            results.forEach(result => {
                if (result.success) successCount++; else failCount++;
            });
            
            if (successCount > 0 && failCount === 0) {
                this.showNotification('Packages Installed', `${successCount} processed successfully.`, 'success');
                this.hidePackageModal();
            } else if (failCount > 0) {
                this.showNotification('Installation Issues', `${successCount} ok, ${failCount} failed. See terminal/console.`, 'warning');
            } else if (results.length > 0) { 
                 this.showNotification('Installation Info', 'Package commands processed. Check terminal for details.', 'info');
            } else { 
                 this.showNotification('Installation Info', 'No valid package commands found to process.', 'warning');
            }
        } catch (error) {
            console.error("JS Error during package installation:", error);
            this.showNotification('System Error', `Package installation failed: ${error.message}`, 'error');
        } finally {
            this.elements.confirmInstall.disabled = false; this.elements.confirmInstall.textContent = 'Install Packages';
        }
    }

    downloadCode() {
        const filename = this.elements.filenameInput.value.trim();
        if (!filename) { this.showNotification('No Filename', 'Enter filename.', 'warning'); return; }
        const finalFilename = filename.endsWith('.py') ? filename : `${filename}.py`;
        const code = this.editorManager.getCode();
        if (!code.trim()) { this.showNotification('No Code', 'Editor empty.', 'warning'); return; }
        try {
            const blob = new Blob([code], { type: 'text/x-python;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = finalFilename;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(url);
            this.hideDownloadModal();
            this.showNotification('Downloaded', `"${finalFilename}" saved.`, 'success');
        } catch (error) { this.showNotification('Download Error', `Failed: ${error.message}`, 'error'); }
    }

    showNotification(title, message, type = 'info', duration = 5000) {
        if (this.notificationManager) return this.notificationManager.show(title, message, type, duration);
        console.warn("Notification (manager unavailable):", title, message); return null;
    }
    updateStatus(text, type = 'normal') {
        this.elements.status.textContent = text; this.elements.status.className = `status ${type}`;
    }
    getState() {
        return { isInitialized: this.isInitialized, pyodideReady: this.pyodideManager.isReady, editorReady: this.editorManager.isReady, installedPackages: this.pyodideManager.getInstalledPackages(), currentCode: this.editorManager.getCode(), executionCount: this.executionCount, lastExecutionTime: this.lastExecutionTime, theme: this.isDarkTheme ? 'dark' : 'light', panelSizes: { editor: this.elements.editorSection?.style.flexBasis, terminal: this.elements.terminalSection?.style.flexBasis }};
    }
    loadCode(code, source = "programmatic") {
        this.editorManager.setCode(code);
        if (source !== "initialRestore") {
            this.showNotification('Code Loaded', 'Code loaded into editor.', 'success');
        }
    }
    loadExample(exampleName) {
        const examples = {
            basic: this.editorManager.defaultCode,
            matplotlib_plot: `# To see plots in the IDE terminal, first run this line:
enable_ide_plotting()

# Then, your Matplotlib code:
import matplotlib.pyplot as plt
import numpy as np

x_coords = np.linspace(0, 2 * np.pi, 60) 
y_coords = np.sin(x_coords)

plt.figure(figsize=(5,3)) 
plt.plot(x_coords, y_coords, marker='o', linestyle='-')
plt.title('Simple Sine Wave for IDE')
plt.xlabel('X-axis values')
plt.ylabel('sin(X-axis values)')
plt.grid(True)
plt.show() 

print("\\nPlot attempted. If Matplotlib is installed and plotting enabled, it should appear above.")`
        };
        if (examples[exampleName]) {
            this.loadCode(examples[exampleName]);
            this.showNotification('Example Loaded', `"${exampleName}" example is ready.`, 'info');
        } else { this.showNotification('Not Found', `Example "${exampleName}" unavailable.`, 'warning'); }
    }
    exportSession() {
        const state = this.getState();
        const session = { timestamp: new Date().toISOString(), version: 'AgentCode-2.3', code: state.currentCode, installedPackages: state.installedPackages, terminalHistory: this.terminalManager.getHistory(), executionCount: state.executionCount, theme: state.theme, panelSizes: state.panelSizes };
        try { return JSON.stringify(session, null, 2); }
        catch (error) { this.showNotification('Export Error', `Failed: ${error.message}`, 'error'); return null; }
    }
    async importSession(sessionDataString) {
        try {
            const session = JSON.parse(sessionDataString);
            if (!session.version || !session.timestamp || typeof session.code === 'undefined') throw new Error('Invalid session format.');
            this.showNotification('Importing Session', 'Please wait...', 'info', 2000);
            this.loadCode(session.code, "sessionImport");
            if (session.installedPackages && Array.isArray(session.installedPackages) && session.installedPackages.length > 0) {
                const pipCommands = session.installedPackages.map(pkg => `pip install ${pkg}`).join('\n');
                this.elements.packageInput.value = pipCommands;
                await this.installPackages();
            }
            if (session.theme) { this.isDarkTheme = session.theme === 'dark'; this.applyInitialTheme(); }
            if (session.panelSizes && session.panelSizes.editor && session.panelSizes.terminal) {
                this.elements.editorSection.style.flexBasis = session.panelSizes.editor;
                this.elements.terminalSection.style.flexBasis = session.panelSizes.terminal;
                localStorage.setItem('agentcode-editor-flex-basis', session.panelSizes.editor);
                localStorage.setItem('agentcode-terminal-flex-basis', session.panelSizes.terminal);
                if (this.editorManager.isReady) this.editorManager.resize();
            }
            this.showNotification('Session Restored', 'Session imported successfully.', 'success');
        } catch (error) { 
            if (this.terminalManager && this.terminalManager._ensureContainer()) {
                this.terminalManager.writeLine(`❌ Import Session Error: ${error.message}`, 'error');
            }
            this.showNotification('Import Failed', `Could not import: ${error.message}`, 'error'); 
        }
    }
    reset() {
        if (confirm('Reset IDE? Clears code, history, panel sizes, and session packages.')) {
            this.editorManager.setCode(this.editorManager.defaultCode);
            try { 
                localStorage.removeItem(this.editorManager.localStorageKey);
            } catch (e) { console.error('Failed to clear saved code from LS', e); }
            this.clearTerminal();
            this.pyodideManager.installedPackages.clear();
            this.executionCount = 0; this.lastExecutionTime = null;
            try {
                localStorage.removeItem('agentcode-editor-flex-basis'); localStorage.removeItem('agentcode-terminal-flex-basis');
                this.elements.editorSection.style.flexBasis = ''; this.elements.terminalSection.style.flexBasis = '';
                if (this.editorManager.isReady) this.editorManager.resize();
            } catch (e) { console.error('Failed to clear panel sizes from LS', e); }
            this.showNotification('IDE Reset', 'IDE has been reset.', 'info');
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const ide = new PythonIDE();
        await ide.initialize();
        window.agentIDE = ide; 
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5') { e.preventDefault(); ide.executeCode(); }
            if (e.shiftKey && (e.ctrlKey || e.metaKey) && (e.key === 'R' || e.key === 'r')) { e.preventDefault(); ide.reset(); }
        });
    } catch (error) {
        console.error('FATAL: Failed to start AgentCode IDE:', error);
        const statusEl = document.getElementById('status'); if (statusEl) { statusEl.textContent = 'Critical Error!'; statusEl.className = 'status error'; }
        const terminalEl = document.getElementById('terminalContent');
        if (terminalEl) {
            const errColor = getComputedStyle(document.documentElement).getPropertyValue('--accent-red').trim() || '#f85149';
            terminalEl.innerHTML = `<span style="color: ${errColor};">❌ CRITICAL ERROR: IDE FAILED TO START.<br>Details: ${error.message}<br>Please refresh.</span>`;
        }
        const notificationContainer = document.getElementById('notificationContainer');
        if (notificationContainer) {
            const notif = document.createElement('div');
            notif.className = 'notification error permanent-error';
            notif.innerHTML = `<div class="notification-header"><span class="notification-title">Critical Failure</span></div><div class="notification-body">IDE could not start: ${error.message}. Please refresh.</div>`;
            notificationContainer.appendChild(notif);
        } else {
            alert(`Critical Error: IDE failed to start. ${error.message}. Please refresh.`);
        }
    }
});