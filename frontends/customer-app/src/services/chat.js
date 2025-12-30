import { fetchAuthSession } from 'aws-amplify/auth'

/**
 * Chat Service
 * WebSocket-based real-time chat service for AI assistant
 * Implements Requirements 7.1, 7.2, 7.3, 7.4 from requirements.md
 */
class ChatService {
  constructor() {
    this.ws = null
    this.sessionId = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000 // Start with 1 second
    this.handlers = {
      onMessage: null,
      onTyping: null,
      onConnect: null,
      onDisconnect: null,
      onError: null
    }
  }

  /**
   * Get WebSocket URL from environment
   */
  getWebSocketUrl() {
    const wsUrl = import.meta.env.VITE_WEBSOCKET_URL
    if (!wsUrl) {
      throw new Error('VITE_WEBSOCKET_URL not configured')
    }

    // Remove trailing slash if present
    return wsUrl.replace(/\/$/, '')
  }

  /**
   * Get authentication token
   */
  async getAuthToken() {
    try {
      const session = await fetchAuthSession()
      return session.tokens?.idToken?.toString()
    } catch (error) {
      console.warn('No active session for chat')
      return null
    }
  }

  /**
   * Generate or retrieve session ID
   */
  getSessionId() {
    if (!this.sessionId) {
      // Try to restore from localStorage
      this.sessionId = localStorage.getItem('chatSessionId')

      if (!this.sessionId) {
        // Generate new session ID
        this.sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        localStorage.setItem('chatSessionId', this.sessionId)
      }
    }
    return this.sessionId
  }

  /**
   * Connect to WebSocket
   */
  async connect(handlers = {}) {
    // Store handlers
    this.handlers = { ...this.handlers, ...handlers }

    try {
      // Get auth token (optional - WebSocket API doesn't require auth yet)
      const token = await this.getAuthToken()
      const sessionId = this.getSessionId()

      // Build WebSocket URL with session ID
      // Note: Token is included but not validated by the API yet
      // This allows for future authentication implementation
      const wsUrl = `${this.getWebSocketUrl()}?sessionId=${sessionId}${token ? `&token=${encodeURIComponent(token)}` : ''}`

      // Create WebSocket connection
      this.ws = new WebSocket(wsUrl)

      // Set up event handlers
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.reconnectDelay = 1000

        if (this.handlers.onConnect) {
          this.handlers.onConnect()
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Handle different message types
          if (data.type === 'typing') {
            if (this.handlers.onTyping) {
              this.handlers.onTyping()
            }
          } else if (data.type === 'message') {
            if (this.handlers.onMessage) {
              this.handlers.onMessage(data)
            }
          } else {
            // Default to message handler
            if (this.handlers.onMessage) {
              this.handlers.onMessage(data)
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        if (this.handlers.onError) {
          this.handlers.onError(error)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        if (this.handlers.onDisconnect) {
          this.handlers.onDisconnect()
        }

        // Attempt to reconnect
        this.attemptReconnect()
      }

      return true
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error)
      if (this.handlers.onError) {
        this.handlers.onError(error)
      }
      return false
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      if (this.handlers.onError) {
        this.handlers.onError(new Error('Failed to reconnect to chat service'))
      }
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect(this.handlers)
    }, delay)
  }

  /**
   * Send message through WebSocket
   */
  async sendMessage(content, metadata = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected')
    }

    const message = {
      action: 'sendMessage',
      content,
      sessionId: this.getSessionId(),
      timestamp: Date.now(),
      metadata
    }

    this.ws.send(JSON.stringify(message))
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Load chat history from localStorage
   * In a production app, this would load from the backend API
   */
  async loadHistory() {
    try {
      // For now, load from localStorage
      // In production, this would call the backend API to load chat history
      const historyKey = `chatHistory-${this.getSessionId()}`
      const storedHistory = localStorage.getItem(historyKey)

      if (storedHistory) {
        const history = JSON.parse(storedHistory)
        // Return last 20 messages
        return history.slice(-20)
      }

      return []
    } catch (error) {
      console.error('Failed to load chat history:', error)
      return []
    }
  }

  /**
   * Save message to history
   * In production, this would be handled by the backend
   */
  saveToHistory(message) {
    try {
      const historyKey = `chatHistory-${this.getSessionId()}`
      const storedHistory = localStorage.getItem(historyKey)
      const history = storedHistory ? JSON.parse(storedHistory) : []

      history.push(message)

      // Keep only last 100 messages
      const trimmedHistory = history.slice(-100)
      localStorage.setItem(historyKey, JSON.stringify(trimmedHistory))
    } catch (error) {
      console.error('Failed to save to history:', error)
    }
  }

  /**
   * Clear chat session
   */
  clearSession() {
    const historyKey = `chatHistory-${this.getSessionId()}`
    localStorage.removeItem(historyKey)
    localStorage.removeItem('chatSessionId')
    this.sessionId = null
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

// Export singleton instance
export const chatService = new ChatService()

// Also export the class for testing
export { ChatService }
