import { useState, useEffect } from 'react'
import IDELayout from './components/IDELayout.jsx'
import AuthScreen from './components/AuthScreen.jsx'
import { checkAuthStatus, logoutUser } from './services/api.js'

function App() {
  const [user, setUser] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const authStatus = await checkAuthStatus()
      if (authStatus.authenticated) {
        setUser(authStatus.user)
        setSessionId(authStatus.session_id)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogin = (userData, sessionId) => {
    setUser(userData)
    setSessionId(sessionId)
  }

  const handleLogout = async () => {
    try {
      await logoutUser()
      setUser(null)
      setSessionId(null)
    } catch (error) {
      console.error('Logout failed:', error)
      setUser(null) // Force logout on client side even if server call fails
      setSessionId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="spinner w-8 h-8 border-2 border-primary border-t-transparent rounded-full"></div>
      </div>
    )
  }

  if (!user) {
    return <AuthScreen onLogin={handleLogin} />
  }

  return <IDELayout user={user} onLogout={handleLogout} initialSessionId={sessionId} />
}

export default App
