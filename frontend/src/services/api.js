import axios from 'axios'

// API client configuration
const authApi = axios.create({
  baseURL: 'http://localhost:5000',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Auth API
export const checkAuthStatus = async () => {
  try {
    const response = await authApi.get('/auth')
    return response.data
  } catch (error) {
    return { authenticated: false }
  }
}

export const loginUser = async (username, password) => {
  try {
    const response = await authApi.post('/login', { username, password })
    return response.data
  } catch (error) {
    throw error.response?.data || { message: 'Login failed' }
  }
}

export const registerUser = async (username, password, name, email) => {
  try {
    const response = await authApi.post('/register', { username, password, name, email })
    return response.data
  } catch (error) {
    throw error.response?.data || { message: 'Registration failed' }
  }
}

export const logoutUser = async () => {
  try {
    await authApi.post('/logout')
    return { success: true }
  } catch (error) {
    return { success: false }
  }
}

// Session Management API
export const getUserSessions = async () => {
  try {
    const response = await authApi.get('/sessions')
    return response.data
  } catch (error) {
    throw error.response?.data || { message: 'Failed to get sessions' }
  }
}

export const createNewSession = async (sessionName = null) => {
  try {
    const response = await authApi.post('/sessions/new', { session_name: sessionName })
    return response.data
  } catch (error) {
    throw error.response?.data || { message: 'Failed to create session' }
  }
}

export const activateSession = async (sessionId) => {
  try {
    const response = await authApi.post(`/sessions/${sessionId}/activate`)
    return response.data
  } catch (error) {
    throw error.response?.data || { message: 'Failed to activate session' }
  }
}

// Chat API
export const sendChatMessage = async (request) => {
  const response = await api.post('/api/chat', request)
  return response.data
}

export const applyChanges = async (sessionId, approved, changes) => {
  const response = await api.post('/api/apply-changes', {
    session_id: sessionId,
    approved,
    changes
  })
  return response.data
}

// File operations API
export const performFileOperation = async (operation, sessionId) => {
  const response = await api.post(`/api/file-operation?session_id=${sessionId}`, operation)
  return response.data
}

export const getWorkspaceInfo = async (sessionId) => {
  const response = await api.get(`/api/workspace/${sessionId}`)
  return response.data
}

export const getChatHistory = async (sessionId) => {
  const response = await api.get(`/api/chat-history/${sessionId}`)
  return response.data
}

export const clearChatHistory = async (sessionId) => {
  const response = await api.delete(`/api/chat-history/${sessionId}`)
  return response.data
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api
