/**
 * Admin Insights WebSocket Service
 * 
 * Manages WebSocket connection to the Admin Insights Agent for real-time
 * conversational analytics. Handles authentication, session management,
 * reconnection logic, and message streaming.
 * 
 * Requirements: 1.1, 1.2, 4.1, 4.2
 */

import { fetchAuthSession } from 'aws-amplify/auth'

class AdminInsightsService {
  constructor() {
    this.ws = null
    this.connectionId = null
    this.sessionId = null
    this.isConnecting = false
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000 // Start with 1 second
    this.maxReconnectDelay = 30000 // Max 30 seconds
    this.messageHandlers = []
    this.errorHandlers = []
    this.connectionHandlers = []
    this.reconnectTimer = null
    this.heartbeatInterval = null
    this.pendingMessages = []
  }

  /**
   * Connect to the Admin Insights WebSocket API
   * Authenticates using Cognito JWT token
   */
  async connect() {
    if (this.isConnecting || this.isConnected) {
      console.log('Already connected or connecting')
      return
    }

    this.isConnecting = true

    try {
      // Get JWT token from Cognito
      const session = await fetchAuthSession()
      const token = session.tokens?.idToken?.toString()

      if (!token) {
        throw new Error('No authentication token available')
      }

      // Get WebSocket URL from environment
      const wsUrl = import.meta.env.VITE_ADMIN_INSIGHTS_WEBSOCKET_URL
      if (!wsUrl) {
        throw new Error('VITE_ADMIN_INSIGHTS_WEBSOCKET_URL not configured')
      }

      // Load session ID from localStorage if exists
      this.sessionId = this._loadSessionId()

      // Connect to WebSocket with token as query parameter
      const url = `${wsUrl}?token=${encodeURIComponent(token)}`
      this.ws = new WebSocket(url)

      // Set up event handlers
      this.ws.onopen = this._handleOpen.bind(this)
      this.ws.onmessage = this._handleMessage.bind(this)
      this.ws.onerror = this._handleError.bind(this)
      this.ws.onclose = this._handleClose.bind(this)

    } catch (error) {
      console.error('Failed to connect to Admin Insights:', error)
      this.isConnecting = false
      this._notifyError(error)
      this._scheduleReconnect()
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false
    this.isConnecting = false
    this.connectionId = null
  }

  /**
   * Send a message to the agent
   * @param {string} message - User message text
   */
  async sendMessage(message) {
    if (!this.isConnected) {
      console.warn('Not connected, queueing message')
      this.pendingMessages.push(message)
      await this.connect()
      return
    }

    try {
      const payload = {
        action: 'sendMessage',
        message: message,
        sessionId: this.sessionId,
        timestamp: Date.now()
      }

      this.ws.send(JSON.stringify(payload))
    } catch (error) {
      console.error('Failed to send message:', error)
      this._notifyError(error)
    }
  }

  /**
   * Register a message handler
   * @param {Function} handler - Callback function (message) => void
   */
  onMessage(handler) {
    this.messageHandlers.push(handler)
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Register an error handler
   * @param {Function} handler - Callback function (error) => void
   */
  onError(handler) {
    this.errorHandlers.push(handler)
    return () => {
      this.errorHandlers = this.errorHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Register a connection status handler
   * @param {Function} handler - Callback function (isConnected) => void
   */
  onConnectionChange(handler) {
    this.connectionHandlers.push(handler)
    return () => {
      this.connectionHandlers = this.connectionHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      sessionId: this.sessionId,
      reconnectAttempts: this.reconnectAttempts
    }
  }

  /**
   * Clear session (start fresh conversation)
   */
  clearSession() {
    this.sessionId = null
    this._saveSessionId(null)
  }

  // Private methods

  _handleOpen(event) {
    console.log('WebSocket connected to Admin Insights')
    this.isConnected = true
    this.isConnecting = false
    this.reconnectAttempts = 0
    this.reconnectDelay = 1000

    // Generate or retrieve session ID
    if (!this.sessionId) {
      this.sessionId = this._generateSessionId()
      this._saveSessionId(this.sessionId)
    }

    // Notify connection handlers
    this._notifyConnectionChange(true)

    // Start heartbeat
    this._startHeartbeat()

    // Send any pending messages
    this._sendPendingMessages()
  }

  _handleMessage(event) {
    try {
      const data = JSON.parse(event.data)

      // Handle different message types
      switch (data.type) {
        case 'chunk':
          // Streaming response chunk
          this._notifyMessage({
            type: 'chunk',
            content: data.content,
            timestamp: Date.now()
          })
          break

        case 'complete':
          // Response complete
          this._notifyMessage({
            type: 'complete',
            content: data.content,
            timestamp: Date.now()
          })
          break

        case 'error':
          // Error from agent
          this._notifyMessage({
            type: 'error',
            content: data.content,
            error: data.error,
            timestamp: Date.now()
          })
          break

        case 'connection':
          // Connection acknowledgment
          this.connectionId = data.connectionId
          if (data.sessionId) {
            this.sessionId = data.sessionId
            this._saveSessionId(data.sessionId)
          }
          break

        case 'pong':
          // Heartbeat response
          break

        default:
          console.warn('Unknown message type:', data.type)
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  _handleError(event) {
    console.error('WebSocket error:', event)
    this._notifyError(new Error('WebSocket connection error'))
  }

  _handleClose(event) {
    console.log('WebSocket closed:', event.code, event.reason)
    this.isConnected = false
    this.isConnecting = false
    this.connectionId = null

    // Stop heartbeat
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }

    // Notify connection handlers
    this._notifyConnectionChange(false)

    // Attempt reconnection if not a normal closure
    if (event.code !== 1000 && event.code !== 1001) {
      this._scheduleReconnect()
    }
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      this._notifyError(new Error('Failed to reconnect after multiple attempts'))
      return
    }

    this.reconnectAttempts++
    
    // Exponential backoff with jitter
    const jitter = Math.random() * 1000
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) + jitter,
      this.maxReconnectDelay
    )

    console.log(`Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  _startHeartbeat() {
    // Send ping every 30 seconds to keep connection alive
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.ws) {
        try {
          this.ws.send(JSON.stringify({ action: 'ping' }))
        } catch (error) {
          console.error('Failed to send heartbeat:', error)
        }
      }
    }, 30000)
  }

  _sendPendingMessages() {
    while (this.pendingMessages.length > 0 && this.isConnected) {
      const message = this.pendingMessages.shift()
      this.sendMessage(message)
    }
  }

  _notifyMessage(message) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        console.error('Error in message handler:', error)
      }
    })
  }

  _notifyError(error) {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error)
      } catch (err) {
        console.error('Error in error handler:', err)
      }
    })
  }

  _notifyConnectionChange(isConnected) {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(isConnected)
      } catch (error) {
        console.error('Error in connection handler:', error)
      }
    })
  }

  _generateSessionId() {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  _saveSessionId(sessionId) {
    if (sessionId) {
      localStorage.setItem('adminInsightsSessionId', sessionId)
    } else {
      localStorage.removeItem('adminInsightsSessionId')
    }
  }

  _loadSessionId() {
    return localStorage.getItem('adminInsightsSessionId')
  }
}

// Export singleton instance
export const adminInsightsService = new AdminInsightsService()
export default adminInsightsService
