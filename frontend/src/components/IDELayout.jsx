import { useState, useEffect, useCallback, useRef } from 'react'
import { Editor } from '@monaco-editor/react'
import { 
  FileText, 
  MessageSquare, 
  Play, 
  Settings, 
  User, 
  LogOut,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  FolderOpen,
  File,
  Folder,
  Plus,
  Trash2,
  Download,
  Upload,
  Terminal,
  Sun,
  Moon
} from 'lucide-react'
import { sendChatMessage, applyChanges, getWorkspaceInfo, createNewSession as createNewSessionAPI, getUserSessions, performFileOperation, getChatHistory, clearChatHistory as clearChatHistoryAPI } from '../services/api.js'
import toast from 'react-hot-toast'

export default function IDELayout({ user, onLogout, initialSessionId }) {
  const [code, setCode] = useState('# Welcome to AgentCode\n\nYour AI-powered development environment is ready!\n\nTo get started:\n1. Ask your AI assistant to create a project\n2. Use the chat to request code, files, or explanations\n3. Execute code using the Run button\n\nExample requests:\n- "Create a simple calculator in HTML/CSS/JS"\n- "Build a Python Flask web server"\n- "Make a React component for a todo list"\n\nHappy coding! 🚀')
  const [chatMessages, setChatMessages] = useState([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [sessionId, setSessionId] = useState(initialSessionId || null)
  const [userSessions, setUserSessions] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState('')
  const [progressMessage, setProgressMessage] = useState('')
  const [pendingChanges, setPendingChanges] = useState(null)
  const [workspaceFiles, setWorkspaceFiles] = useState([])
  const [currentFile, setCurrentFile] = useState('README.md')
  const [sidebarTab, setSidebarTab] = useState('chat')
  const [executionOutput, setExecutionOutput] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [fileContent, setFileContent] = useState({
    'README.md': '# Welcome to AgentCode\n\nYour AI-powered development environment is ready!\n\nTo get started:\n1. Ask your AI assistant to create a project\n2. Use the chat to request code, files, or explanations\n3. Execute code using the Run button\n\nExample requests:\n- "Create a simple calculator in HTML/CSS/JS"\n- "Build a Python Flask web server"\n- "Make a React component for a todo list"\n\nHappy coding! 🚀'
  })
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    const saved = localStorage.getItem('agentcode_dark_theme')
    return saved ? JSON.parse(saved) : true
  })
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState(null)
  const [pyodideStatus, setPyodideStatus] = useState('loading') // 'loading', 'ready', 'error'
  const [pyodideError, setPyodideError] = useState(null)
  
  const chatMessagesEndRef = useRef(null)
  const saveTimeoutRef = useRef(null)

  useEffect(() => {
    // Initialize session from auth or database
    if (initialSessionId) {
      setSessionId(initialSessionId)
      loadWorkspaceFiles(initialSessionId)
      loadUserSessions()
    } else {
      // If no initial session, try to create one
      createNewSessionForUser()
    }
    initializePyodide()
  }, [initialSessionId])

  // Create a new session for user if none exists
  const createNewSessionForUser = async () => {
    try {
      const response = await createNewSessionAPI()
      if (response.success) {
        setSessionId(response.session_id)
        loadWorkspaceFiles(response.session_id)
        loadUserSessions()
      }
    } catch (error) {
      console.error('Failed to create initial session:', error)
      // Set a temporary session ID as fallback
      const fallbackSessionId = `temp_${Date.now()}`
      setSessionId(fallbackSessionId)
    }
  }

  // Load user sessions from database
  const loadUserSessions = async () => {
    try {
      const response = await getUserSessions()
      if (response.success) {
        setUserSessions(response.sessions)
      }
    } catch (error) {
      console.error('Failed to load user sessions:', error)
    }
  }

  // Save theme preference and apply to document
  useEffect(() => {
    localStorage.setItem('agentcode_dark_theme', JSON.stringify(isDarkTheme))
    
    // Apply theme class to document element
    if (isDarkTheme) {
      document.documentElement.classList.remove('light')
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.classList.add('light')
    }
  }, [isDarkTheme])

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatMessagesEndRef.current) {
      chatMessagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatMessages])

  const getLanguageFromExtension = (filename) => {
    if (!filename) return 'markdown'
    const ext = filename.split('.').pop()?.toLowerCase()
    const languageMap = {
      'py': 'python',
      'js': 'javascript', 
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'html': 'html',
      'css': 'css',
      'json': 'json',
      'md': 'markdown',
      'txt': 'plaintext',
      'sql': 'sql',
      'sh': 'shell',
      'yml': 'yaml',
      'yaml': 'yaml'
    }
    return languageMap[ext] || 'plaintext'
  }

  const createNewSession = async () => {
    try {
      const response = await createNewSessionAPI()
      if (response.success) {
        setSessionId(response.session_id)
        setChatMessages([])
        setWorkspaceFiles([{ name: 'README.md', type: 'file', path: 'README.md' }])
        setCurrentFile('README.md')
        setCode(fileContent['README.md'] || '# Welcome to AgentCode\n\nYour workspace is ready!')
        loadUserSessions() // Refresh sessions list
        toast.success('New session created!')
        console.log('Created new session:', response.session_id)
      }
    } catch (error) {
      console.error('Failed to create new session:', error)
      toast.error('Failed to create new session')
    }
  }

  const initializePyodide = async () => {
    try {
      console.log('Starting Pyodide initialization...')
      setPyodideStatus('loading')
      
      // Check if Pyodide is already loaded
      if (window.pyodide) {
        console.log('Pyodide already loaded')
        setPyodideStatus('ready')
        return
      }

      // Check if loadPyodide function is available
      if (typeof loadPyodide === 'undefined') {
        console.log('Loading Pyodide script...')
        
        // Load Pyodide script
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js'
        script.async = true
        
        // Create promise to wait for script loading
        const scriptLoadPromise = new Promise((resolve, reject) => {
          script.onload = resolve
          script.onerror = reject
        })
        
        document.head.appendChild(script)
        await scriptLoadPromise
        console.log('Pyodide script loaded successfully')
      }
      
      // Initialize Pyodide
      console.log('Initializing Pyodide runtime...')
      toast.loading('Initializing Python environment...', {
        id: 'pyodide-init',
        duration: 0 // Keep until manually dismissed
      })
      
      window.pyodide = await loadPyodide({
        indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
        stdout: (text) => console.log('Pyodide stdout:', text),
        stderr: (text) => console.warn('Pyodide stderr:', text)
      })
      
      console.log('Pyodide initialized successfully!')
      setPyodideStatus('ready')
      setPyodideError(null)
      
      // Dismiss loading toast and show success
      toast.dismiss('pyodide-init')
      toast.success('🐍 Python environment is ready!', {
        duration: 4000,
        icon: '✅'
      })
      
    } catch (error) {
      console.error('Failed to initialize Pyodide:', error)
      setPyodideStatus('error')
      setPyodideError(error.message || 'Unknown error')
      
      toast.dismiss('pyodide-init')
      toast.error(`Failed to initialize Python environment: ${error.message}`, {
        duration: 6000
      })
    }
  }

  const loadWorkspaceFiles = async (sid) => {
    try {
      const workspaceInfo = await getWorkspaceInfo(sid || sessionId)
      if (workspaceInfo.files && workspaceInfo.files.length > 0) {
        setWorkspaceFiles(workspaceInfo.files)
        
        // Load content for the current file if it exists in the workspace
        const currentFileExists = workspaceInfo.files.find(f => f.name === currentFile)
        if (currentFileExists && sid) {
          // Load the current file content
          selectFile(currentFile)
        }
      } else {
        // For new sessions, only show README.md
        setWorkspaceFiles([
          { name: 'README.md', type: 'file', path: 'README.md' }
        ])
      }
      
      // Load chat history for this session
      if (sid) {
        loadChatHistory(sid)
      }
    } catch (error) {
      console.error('Failed to load workspace:', error)
      // Set only README for new workspace
      setWorkspaceFiles([
        { name: 'README.md', type: 'file', path: 'README.md' }
      ])
    }
  }

  const loadChatHistory = async (sid) => {
    try {
      const chatData = await getChatHistory(sid || sessionId)
      if (chatData.conversation_history && chatData.conversation_history.length > 0) {
        // Convert database format to frontend format
        const formattedMessages = chatData.conversation_history.map((msg, index) => ({
          role: msg.role || (index % 2 === 0 ? 'user' : 'assistant'),
          content: msg.content || msg.message || '',
          timestamp: msg.timestamp || new Date().toISOString(),
          id: msg.id || index
        }))
        setChatMessages(formattedMessages)
        console.log(`Loaded ${formattedMessages.length} chat messages from history`)
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
      // Don't show error to user, just continue with empty chat
    }
  }

  const clearChatHistory = async () => {
    try {
      await clearChatHistoryAPI(sessionId)
      setChatMessages([])
      toast.success('Chat history cleared successfully')
    } catch (error) {
      console.error('Failed to clear chat history:', error)
      toast.error('Failed to clear chat history')
    }
  }

  // Auto-save function with debouncing
  const saveFileToBackend = async (fileName, content) => {
    if (!fileName || !sessionId || fileName === 'README.md') {
      return // Don't save README.md or if no session
    }

    try {
      setIsSaving(true)
      await performFileOperation({
        operation: 'modify',
        file_path: fileName,
        content: content
      }, sessionId)
      
      setLastSaved(new Date())
      console.log(`Auto-saved ${fileName}`)
    } catch (error) {
      console.error('Auto-save failed:', error)
      // Don't show error toast for auto-save failures to avoid spam
    } finally {
      setIsSaving(false)
    }
  }

  // Manual save function
  const saveCurrentFile = async () => {
    if (!currentFile || !sessionId) {
      toast.error('No file to save')
      return
    }
    
    try {
      setIsSaving(true)
      await performFileOperation({
        operation: 'modify',
        file_path: currentFile,
        content: code
      }, sessionId)
      
      setLastSaved(new Date())
      toast.success(`Saved ${currentFile}`)
    } catch (error) {
      console.error('Manual save failed:', error)
      toast.error(`Failed to save ${currentFile}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Keyboard shortcut handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveCurrentFile()
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [currentFile, code, sessionId])

  // Debounced auto-save
  const debouncedSave = useCallback((fileName, content) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    saveTimeoutRef.current = setTimeout(() => {
      saveFileToBackend(fileName, content)
    }, 2000) // Save after 2 seconds of no changes
  }, [sessionId])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  const executeCode = async () => {
    if (!code.trim()) {
      toast.error('No code to execute')
      return
    }

    setIsExecuting(true)
    setExecutionOutput('Executing...')

    try {
      // Check if current file is a Python file
      const isPythonFile = currentFile.endsWith('.py')
      
      if (isPythonFile) {
        // Execute Python code with Pyodide
        if (pyodideStatus === 'loading') {
          setExecutionOutput('⏳ Python environment is still loading. Please wait for initialization to complete.')
          toast.info('Python environment is still loading...', {
            duration: 3000
          })
          return
        } else if (pyodideStatus === 'error') {
          setExecutionOutput(`❌ Python environment failed to load: ${pyodideError}\n\nPlease refresh the page to retry.`)
          toast.error('Python environment is not available')
          return
        } else if (pyodideStatus === 'ready' && window.pyodide) {
          // Capture stdout
          await window.pyodide.runPython(`
            import sys
            from io import StringIO
            sys.stdout = StringIO()
          `)
          
          // Execute the code
          await window.pyodide.runPython(code)
          
          // Get the output
          const output = await window.pyodide.runPython('sys.stdout.getvalue()')
          setExecutionOutput(output || 'Python code executed successfully (no output)')
          
          // Reset stdout
          await window.pyodide.runPython('sys.stdout = sys.__stdout__')
        } else {
          setExecutionOutput('🔄 Python environment is not ready yet. Please wait for initialization to complete.')
          toast.warning('Python environment not ready yet')
          return
        }
      } else {
        // For non-Python files, show appropriate message
        const fileExt = currentFile.split('.').pop()?.toLowerCase()
        
        switch (fileExt) {
          case 'js':
          case 'jsx':
            setExecutionOutput(`JavaScript files cannot be executed directly in this environment.\n\nTo run JavaScript code:\n1. Create an HTML file\n2. Include your JS file with <script> tag\n3. Open the HTML file in a browser`)
            break
          case 'html':
            setExecutionOutput(`HTML files cannot be executed directly here.\n\nTo view HTML:\n1. Save the file\n2. Open it in a web browser\n3. Or use a local development server`)
            break
          case 'css':
            setExecutionOutput(`CSS files are stylesheets and cannot be executed.\n\nTo use CSS:\n1. Link it to an HTML file with <link> tag\n2. Or include it in <style> tags`)
            break
          case 'md':
            setExecutionOutput(`Markdown files are documentation and cannot be executed.\n\nTo view formatted markdown:\n1. Use a markdown viewer\n2. Or render it in a markdown-enabled application`)
            break
          default:
            setExecutionOutput(`Files with extension '.${fileExt}' cannot be executed in this environment.\n\nOnly Python (.py) files can be executed using the built-in interpreter.`)
        }
        
        toast.info(`Only Python files can be executed. Current file: ${currentFile}`)
      }
      
      if (isPythonFile) {
        toast.success('Python code executed successfully')
      }
    } catch (error) {
      const errorMessage = error.toString()
      setExecutionOutput(`Error: ${errorMessage}`)
      toast.error('Execution failed')
    } finally {
      setIsExecuting(false)
    }
  }

  const createNewFile = async () => {
    const fileName = prompt('Enter file name:')
    if (fileName && fileName.trim()) {
      try {
        const trimmedName = fileName.trim()
        const defaultContent = '# New file\n'
        
        // Create file in backend first
        await performFileOperation({
          operation: 'create',
          file_path: trimmedName,
          content: defaultContent
        }, sessionId)
        
        // Update frontend state after successful backend creation
        const newFile = {
          name: trimmedName,
          type: 'file',
          path: trimmedName
        }
        setWorkspaceFiles(prev => [...prev, newFile])
        setCurrentFile(trimmedName)
        setFileContent(prev => ({
          ...prev,
          [trimmedName]: defaultContent
        }))
        setCode(defaultContent)
        toast.success(`Created ${trimmedName} in workspace`)
      } catch (error) {
        console.error('Failed to create file:', error)
        toast.error(`Failed to create ${fileName.trim()}: ${error.message || 'Unknown error'}`)
      }
    }
  }

  const deleteFile = async (fileName) => {
    if (confirm(`Are you sure you want to delete ${fileName}?`)) {
      try {
        // Delete file from backend first
        await performFileOperation({
          operation: 'delete',
          file_path: fileName
        }, sessionId)
        
        // Update frontend state after successful backend deletion
        setWorkspaceFiles(prev => prev.filter(f => f.name !== fileName))
        
        if (currentFile === fileName) {
          const remainingFiles = workspaceFiles.filter(f => f.name !== fileName)
          if (remainingFiles.length > 0) {
            setCurrentFile(remainingFiles[0].name)
            setCode(fileContent[remainingFiles[0].name] || '')
          } else {
            setCurrentFile('README.md')
            setCode(fileContent['README.md'] || '# Welcome to AgentCode\n\nYour workspace is ready!')
          }
        }
        
        // Remove from local file content cache
        setFileContent(prev => {
          const newContent = { ...prev }
          delete newContent[fileName]
          return newContent
        })
        
        toast.success(`Deleted ${fileName} from workspace`)
      } catch (error) {
        console.error('Failed to delete file:', error)
        toast.error(`Failed to delete ${fileName}: ${error.message || 'Unknown error'}`)
      }
    }
  }

  const selectFile = async (fileName) => {
    // Save current file content
    if (currentFile) {
      setFileContent(prev => ({
        ...prev,
        [currentFile]: code
      }))
    }
    
    // Load selected file
    setCurrentFile(fileName)
    
    // Check if content is already loaded in memory
    if (fileContent[fileName]) {
      setCode(fileContent[fileName])
      return
    }
    
    // If README.md is being loaded, use default content
    if (fileName === 'README.md' && !workspaceFiles.find(f => f.name === 'README.md' && f.size > 0)) {
      const defaultContent = '# Welcome to AgentCode\n\nYour AI-powered development environment is ready!\n\nTo get started:\n1. Ask your AI assistant to create a project\n2. Use the chat to request code, files, or explanations\n3. Execute code using the Run button\n\nExample requests:\n- "Create a simple calculator in HTML/CSS/JS"\n- "Build a Python Flask web server"\n- "Make a React component for a todo list"\n\nHappy coding! 🚀'
      setCode(defaultContent)
      setFileContent(prev => ({ ...prev, [fileName]: defaultContent }))
      return
    }
    
    // Fetch file content from API
    try {
      setCode('Loading...')
      const response = await performFileOperation({
        operation: 'read',
        file_path: fileName
      }, sessionId)
      
      if (response.content !== undefined) {
        setCode(response.content)
        setFileContent(prev => ({ ...prev, [fileName]: response.content }))
      } else {
        // Fallback if no content returned
        setCode(`# Contents of ${fileName}\n`)
      }
    } catch (error) {
      console.error('Failed to load file content:', error)
      toast.error(`Failed to load ${fileName}`)
      setCode(`# Error loading ${fileName}\n# ${error.message || 'Unknown error'}`)
    }
  }

  const handleSendMessage = useCallback(async () => {
    if (!currentMessage.trim() || isLoading) return

    const message = currentMessage.trim()
    setCurrentMessage('')
    setIsLoading(true)
    setProgressMessage('Analyzing request...')

    // Add user message to chat
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }
    setChatMessages(prev => [...prev, userMessage])

    // Add progress message to chat
    const progressMsg = {
      role: 'assistant',
      content: '🔄 Analyzing your request...',
      timestamp: new Date().toISOString(),
      isProgress: true
    }
    setChatMessages(prev => [...prev, progressMsg])

    try {
      // Update progress
      setProgressMessage('Planning approach...')
      setChatMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 && msg.isProgress 
          ? { ...msg, content: '🧠 Planning approach...' }
          : msg
      ))

      // Short delay to show progress
      await new Promise(resolve => setTimeout(resolve, 500))

      setProgressMessage('Running AI agents...')
      setChatMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 && msg.isProgress 
          ? { ...msg, content: '🤖 Running AI agents...' }
          : msg
      ))

      const response = await sendChatMessage({
        message,
        session_id: sessionId,
        current_file: currentFile,
        code_content: code,
        workspace_path: `./workspaces/${sessionId}`
      })

      // Update progress for file operations
      if (response.response.includes('file') || response.response.includes('created') || response.response.includes('workspace')) {
        setProgressMessage('Creating files...')
        setChatMessages(prev => prev.map((msg, idx) => 
          idx === prev.length - 1 && msg.isProgress 
            ? { ...msg, content: '📁 Creating files...' }
            : msg
        ))
        await new Promise(resolve => setTimeout(resolve, 300))
      }

      // Remove progress message and add actual response
      setChatMessages(prev => prev.filter(msg => !msg.isProgress))

      // Add AI response to chat
      const aiMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        requires_confirmation: response.requires_confirmation,
        proposed_changes: response.proposed_changes
      }
      setChatMessages(prev => [...prev, aiMessage])

      if (response.requires_confirmation && response.proposed_changes) {
        setPendingChanges({
          sessionId: response.session_id,
          changes: response.proposed_changes
        })
      }

      // Reload workspace files if new files were created
      if (response.response.includes('created') || response.response.includes('file')) {
        await loadWorkspaceFiles()
      }

    } catch (error) {
      console.error('Chat error:', error)
      
      // Remove progress message
      setChatMessages(prev => prev.filter(msg => !msg.isProgress))
      
      toast.error('Failed to send message')
      
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString()
      }
      setChatMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setProgressMessage('')
    }
  }, [currentMessage, isLoading, sessionId, currentFile, code, loadWorkspaceFiles])

  const handleApproveChanges = async () => {
    if (!pendingChanges) return

    try {
      setIsLoading(true)
      await applyChanges(pendingChanges.sessionId, true, pendingChanges.changes)
      toast.success('Changes applied successfully!')
      setPendingChanges(null)
      
      // Reload workspace files
      await loadWorkspaceFiles()
      
      // Add confirmation message
      const confirmMessage = {
        role: 'assistant',
        content: 'Changes have been applied successfully!',
        timestamp: new Date().toISOString()
      }
      setChatMessages(prev => [...prev, confirmMessage])
      
    } catch (error) {
      console.error('Apply changes error:', error)
      toast.error('Failed to apply changes')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRejectChanges = async () => {
    if (!pendingChanges) return

    try {
      await applyChanges(pendingChanges.sessionId, false)
      setPendingChanges(null)
      toast.success('Changes cancelled')
      
      const cancelMessage = {
        role: 'assistant',
        content: 'Changes have been cancelled. How else can I help you?',
        timestamp: new Date().toISOString()
      }
      setChatMessages(prev => [...prev, cancelMessage])
      
    } catch (error) {
      console.error('Cancel changes error:', error)
      toast.error('Failed to cancel changes')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const renderChatMessage = (message, index) => (
    <div key={index} className={`chat-message p-3 rounded-lg ${
      message.role === 'user' 
        ? 'bg-primary text-primary-foreground ml-4' 
        : 'bg-muted mr-4'
    }`}>
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0">
          {message.role === 'user' ? (
            <User className="w-4 h-4" />
          ) : (
            <MessageSquare className="w-4 h-4" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          <p className="text-xs opacity-70 mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </p>
        </div>
      </div>
      
      {message.requires_confirmation && message.proposed_changes && (
        <div className="mt-3 p-3 bg-accent rounded border">
          <p className="text-sm font-medium mb-2">Proposed Changes:</p>
          <ul className="text-xs space-y-1 mb-3">
            {message.proposed_changes.map((change, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                <span>{change.description}</span>
              </li>
            ))}
          </ul>
          
          {pendingChanges && (
            <div className="flex gap-2">
              <button
                onClick={handleApproveChanges}
                disabled={isLoading}
                className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCircle className="w-3 h-3" />
                Approve
              </button>
              <button
                onClick={handleRejectChanges}
                disabled={isLoading}
                className="flex items-center gap-1 px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 disabled:opacity-50"
              >
                <XCircle className="w-3 h-3" />
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <img 
              src="/assets/agentcode.png" 
              alt="AgentCode Logo" 
              className="h-6 w-6"
              onError={(e) => e.target.style.display = 'none'}
            />
            <h1 className="text-xl font-bold">AgentCode</h1>
          </div>
          <div className="text-sm text-muted-foreground">
            Session: {sessionId ? (sessionId.startsWith('temp_') ? 'Initializing...' : sessionId.slice(-8)) : 'Loading...'}
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <button
            onClick={createNewSession}
            className="px-3 py-2 text-xs bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors"
            title="Start new session"
          >
            New Session
          </button>
          <button
            onClick={() => setIsDarkTheme(!isDarkTheme)}
            className="p-2 hover:bg-accent rounded-lg transition-colors"
            title={isDarkTheme ? "Switch to light theme" : "Switch to dark theme"}
          >
            {isDarkTheme ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <div className="flex items-center gap-2 text-sm">
            <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
              {user.name ? user.name.charAt(0).toUpperCase() : user.username.charAt(0).toUpperCase()}
            </div>
            <span>{user.name || user.username}</span>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-border rounded hover:bg-accent"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 border-r border-border flex flex-col">
          <div className="flex border-b border-border">
            <button
              onClick={() => setSidebarTab('chat')}
              className={`flex-1 flex items-center justify-center gap-2 p-3 text-sm ${
                sidebarTab === 'chat' ? 'bg-accent' : 'hover:bg-accent'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              Chat
            </button>
            <button
              onClick={() => setSidebarTab('files')}
              className={`flex-1 flex items-center justify-center gap-2 p-3 text-sm ${
                sidebarTab === 'files' ? 'bg-accent' : 'hover:bg-accent'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              Files
            </button>
            <button
              onClick={() => setSidebarTab('output')}
              className={`flex-1 flex items-center justify-center gap-2 p-3 text-sm ${
                sidebarTab === 'output' ? 'bg-accent' : 'hover:bg-accent'
              }`}
            >
              <Terminal className="w-4 h-4" />
              Output
            </button>
          </div>

          {sidebarTab === 'chat' ? (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Chat header with clear button */}
              <div className="flex items-center justify-between p-3 border-b border-border">
                <h3 className="text-sm font-medium">Chat</h3>
                <button
                  onClick={clearChatHistory}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
                  title="Clear chat history"
                >
                  <Trash2 className="w-3 h-3" />
                  Clear
                </button>
              </div>
              
              {/* Chat messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
                {chatMessages.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Start a conversation with your AI assistant</p>
                    <p className="text-xs mt-1">Try: "Create a React component" or "Fix this bug"</p>
                  </div>
                ) : (
                  chatMessages.map(renderChatMessage)
                )}
                
                {isLoading && (
                  <div className="flex items-center gap-2 text-muted-foreground text-sm p-3">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {progressMessage || 'AI is thinking...'}
                  </div>
                )}
                
                {/* Scroll anchor */}
                <div ref={chatMessagesEndRef} />
              </div>

              {/* Chat input */}
              <div className="p-4 border-t border-border flex-shrink-0">
                <div className="flex gap-2">
                  <textarea
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={isLoading ? "AI is processing your request..." : "Ask your AI assistant..."}
                    className="flex-1 min-h-[40px] max-h-[120px] p-3 text-sm bg-muted border border-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={isLoading || !currentMessage.trim()}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : sidebarTab === 'files' ? (
            <div className="flex-1 flex flex-col">
              <div className="p-3 border-b border-border">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-sm">Files</h3>
                  <button
                    onClick={createNewFile}
                    className="p-1 hover:bg-accent rounded"
                    title="Create new file"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2">
                {workspaceFiles.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    <File className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No files in workspace</p>
                    <p className="text-xs mt-1">Create files using the + button</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {workspaceFiles.map((file, index) => (
                      <div
                        key={index}
                        className={`flex items-center justify-between p-2 rounded cursor-pointer hover:bg-accent group ${
                          currentFile === file.name ? 'bg-accent' : ''
                        }`}
                        onClick={() => selectFile(file.name)}
                      >
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <File className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate text-sm">{file.name}</span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteFile(file.name)
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded"
                          title="Delete file"
                        >
                          <Trash2 className="w-3 h-3 text-red-600" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col">
              <div className="p-3 border-b border-border">
                <h3 className="font-medium text-sm">Output</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-3">
                <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded font-mono whitespace-pre-wrap min-h-full">
                  {executionOutput || 'No output yet. Run some code to see results here.'}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between p-2 border-b border-border bg-muted">
            <div className="flex items-center gap-2 text-sm">
              <FileText className="w-4 h-4" />
              <span>{currentFile}</span>
              {isSaving && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Saving...</span>
                </div>
              )}
              {lastSaved && !isSaving && (
                <div className="text-xs text-muted-foreground">
                  <span>Saved {lastSaved.toLocaleTimeString()}</span>
                </div>
              )}
            </div>
            
            {/* Pyodide Status Indicator */}
            <div className="flex items-center gap-2 px-2 py-1 text-xs rounded border">
              {pyodideStatus === 'loading' && (
                <div className="flex items-center gap-1 text-amber-600">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Loading Python...</span>
                </div>
              )}
              {pyodideStatus === 'ready' && (
                <div className="flex items-center gap-1 text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Python Ready</span>
                </div>
              )}
              {pyodideStatus === 'error' && (
                <div className="flex items-center gap-1 text-red-600" title={pyodideError}>
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                  <span>Python Error</span>
                </div>
              )}
            </div>
            
            <button 
              onClick={executeCode}
              disabled={isExecuting || pyodideStatus !== 'ready'}
              className="flex items-center gap-2 px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-3 h-3" />
                  Run
                </>
              )}
            </button>
          </div>
          
          <div className="flex-1">
            <Editor
              height="100%"
              language={getLanguageFromExtension(currentFile)}
              value={code}
              onChange={(value) => {
                setCode(value || '')
                // Save current file content when changed
                if (currentFile) {
                  setFileContent(prev => ({
                    ...prev,
                    [currentFile]: value || ''
                  }))
                  
                  // Trigger auto-save to backend
                  debouncedSave(currentFile, value || '')
                }
              }}
              theme={isDarkTheme ? "vs-dark" : "light"}
              options={{
                fontSize: 14,
                fontFamily: 'JetBrains Mono, Consolas, monospace',
                wordWrap: 'on',
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                suggestOnTriggerCharacters: true,
                quickSuggestions: true,
                formatOnPaste: true,
                formatOnType: true,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
