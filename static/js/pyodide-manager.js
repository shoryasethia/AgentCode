// Path: js/pyodide-manager.js
class PyodideManager {
    constructor() {
        this.pyodide = null;
        this.isReady = false;
        this.installedPackages = new Set();
        this.initializationPromise = null;
        this.displayPlotCallback = null; 
    }

    setDisplayPlotCallback(callback) {
        this.displayPlotCallback = callback;
    }

    async _initializePyodide() {
        try {
            this.pyodide = await loadPyodide({
                indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.6/full/"
            });

            if (this.displayPlotCallback) {
                this.pyodide.globals.set('__agent_ide_display_plot_callback__', this.displayPlotCallback);
            } else {
                this.pyodide.globals.set('__agent_ide_display_plot_callback__', (base64_data) => {
                    console.error("CRITICAL: Plot callback not set in PyodideManager. Plot lost.");
                });
            }

            const pythonSetupScript = `
import sys
import io
import base64
import traceback
from contextlib import redirect_stdout, redirect_stderr

class _OutputCapture:
    def __init__(self): self.reset()
    def reset(self): self.stdout, self.stderr = io.StringIO(), io.StringIO()
    def get_output(self): return {'stdout': self.stdout.getvalue(), 'stderr': self.stderr.getvalue()}
_ide_output_capture = _OutputCapture()

_matplotlib_show_customized = False

def _custom_plt_show_for_ide(*args, **kwargs):
    global _ide_output_capture, _matplotlib_show_customized
    js_plot_callback = globals().get('__agent_ide_display_plot_callback__')
    if not js_plot_callback:
        _ide_output_capture.stderr.write("Error: IDE plot display callback not found.\\n")
        return

    try:
        import matplotlib.pyplot as plt
        
        if not plt.get_fignums():
            return

        current_fig = plt.gcf()
        if not current_fig.axes and not current_fig.get_children()[1:]:
            _ide_output_capture.stderr.write("Warning: plt.show() called on an empty figure.\\n")
            plt.clf(); plt.close(current_fig)
            return

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=96)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        js_plot_callback(f"data:image/png;base64,{img_base64}")
        plt.clf(); plt.close(current_fig)
    except ImportError:
        _ide_output_capture.stderr.write("Error: Matplotlib not found. Install it first.\\n")
    except Exception as e:
        _ide_output_capture.stderr.write(f"Error during plot generation for IDE: {str(e)}\\n{traceback.format_exc()}\\n")
        try:
            import matplotlib.pyplot as plt
            if plt.get_fignums(): plt.close('all')
        except: pass

def enable_ide_plotting():
    global _matplotlib_show_customized, _ide_output_capture
    if _matplotlib_show_customized:
        return
    try:
        import matplotlib
        current_backend = matplotlib.get_backend()
        if current_backend.lower() != 'agg':
            try:
                matplotlib.use('AGG')
            except Exception as e:
                _ide_output_capture.stderr.write(f"Warning: Could not set Matplotlib backend to 'AGG'. Current: {current_backend}. Error: {e}\\n")
        
        import matplotlib.pyplot as plt
        plt.show = _custom_plt_show_for_ide
        _matplotlib_show_customized = True
    except ImportError:
        _ide_output_capture.stderr.write("Error: Matplotlib not found. Cannot enable IDE plotting. Install it first.\\n")
    except Exception as e:
        _ide_output_capture.stderr.write(f"Error enabling IDE plotting: {str(e)}\\n")

__builtins__.enable_ide_plotting = enable_ide_plotting
            `;
            await this.pyodide.runPythonAsync(pythonSetupScript);
            this.isReady = true;
            return true;
        } catch (error) {
            console.error('FATAL: Pyodide initialization or Python setup script failed:', error);
            throw error;
        }
    }

    async initialize() {
        if (!this.initializationPromise) {
            this.initializationPromise = this._initializePyodide();
        }
        return this.initializationPromise;
    }

    async installPackage(packageName) {
        if (!this.isReady) throw new Error('Pyodide is not ready.');
        const lowerPkgName = String(packageName).toLowerCase().trim();
        if (!lowerPkgName) return { success: false, message: "Package name empty."};
        if (this.installedPackages.has(lowerPkgName)) {
            return { success: true, message: `${packageName} already loaded.` };
        }
        try {
            await this.pyodide.loadPackage([packageName]);
            this.installedPackages.add(lowerPkgName);
            return { success: true, message: `Installed ${packageName}` };
        } catch (error) {
            return { success: false, message: `Failed to install ${packageName}: ${error.message}` };
        }
    }

    async executeCode(code) {
        if (!this.isReady) throw new Error('Pyodide is not ready.');
        try {
            await this.pyodide.runPythonAsync('_ide_output_capture.reset()');

            // Prepare the user's code for safe embedding in a Python triple-quoted string
            const escapedCode = code
                .replace(/\\/g, '\\\\')        // 1. Escape all backslashes FIRST
                .replace(/"""/g, '\\"\\"\\"'); // 2. Escape triple-double-quotes to prevent breaking our exec string

            const executionWrapperScript = `
from contextlib import redirect_stdout, redirect_stderr
import traceback

_exec_success_ = True
_exec_error_msg_ = None
with redirect_stdout(_ide_output_capture.stdout), redirect_stderr(_ide_output_capture.stderr):
    try:
        exec("""${escapedCode}""") # Use the fully escapedCode
    except Exception as _e_:
        _exec_success_ = False
        _exec_error_msg_ = str(_e_)
        _ide_output_capture.stderr.write(traceback.format_exc())
{
    'success': _exec_success_,
    'error': _exec_error_msg_,
    'output': _ide_output_capture.get_output()
}
            `;
            const resultProxy = await this.pyodide.runPythonAsync(executionWrapperScript);
            const jsResult = resultProxy.toJs({ dict_converter: Object.fromEntries });
            resultProxy.destroy();

            if (jsResult && typeof jsResult.output === 'object' && jsResult.output !== null) {
                return {
                    success: jsResult.success, error: jsResult.error,
                    stdout: jsResult.output.stdout || '', stderr: jsResult.output.stderr || ''
                };
            } else {
                console.error("Pyodide result error. Structure:", jsResult);
                return { success: false, error: "Internal Pyodide Error: Malformed result.", stdout: '', stderr: "Internal Pyodide Error: Malformed result." };
            }
        } catch (jsError) {
            console.error("JS Error during Pyodide code execution:", jsError);
            return { success: false, error: `JS error: ${jsError.message}`, stdout: '', stderr: `JS error: ${jsError.message}` };
        }
    }

    _parsePipCommand(command) {
        const pipRegex = /^pip\s+install\s+(.+)$/i;
        const match = command.trim().match(pipRegex);
        if (!match || !match[1]) return [];
        return match[1].split(/\s+/).map(pkg => pkg.trim()).filter(pkg => pkg.length > 0 && !pkg.startsWith('-'));
    }

    async installFromPipCommands(commands) {
        const results = [];
        const lines = String(commands).trim().split('\n').filter(line => line.trim().length > 0);
        if (lines.length === 0) return [{ command: "(empty)", success: false, message: "No commands." }];

        for (const line of lines) {
            const packagesToInstall = this._parsePipCommand(line);
            if (packagesToInstall.length === 0) {
                results.push({ command: line, success: false, message: `Invalid: "${line}"`});
                continue;
            }
            for (const pkg of packagesToInstall) {
                const result = await this.installPackage(pkg);
                results.push({ command: line, package: pkg, ...result });
            }
        }
        return results;
    }
    getAvailablePackages() { return ['numpy', 'pandas', 'matplotlib', 'scipy', 'scikit-learn', 'sympy', 'micropip', 'requests', 'beautifulsoup4', 'lxml', 'pillow', 'networkx', 'bokeh', 'plotly', 'seaborn', 'folium']; }
    isPackageInstalled(packageName) { return this.installedPackages.has(String(packageName).toLowerCase().trim()); }
    getInstalledPackages() { return Array.from(this.installedPackages); }
}