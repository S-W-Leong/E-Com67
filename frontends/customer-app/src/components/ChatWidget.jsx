import React, { useState, useEffect, useRef } from 'react'
import { MessageCircle, X, Send, Minimize2, Loader2 } from 'lucide-react'
import { chatService } from '../services/chat'

/**
 * AI Chat Widget
 * Real-time chat interface for customer support and product recommendations
 * Implements Requirements 7.1, 7.2, 7.3, 7.4 from requirements.md
 */
const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  /**
   * Initialize chat and load history when opened
   */
  useEffect(() => {
    if (isOpen && !isConnected) {
      initializeChat()
    }

    // Cleanup on unmount
    return () => {
      if (isConnected) {
        chatService.disconnect()
      }
    }
  }, [isOpen])

  /**
   * Auto-scroll to bottom when new messages arrive
   */
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  /**
   * Initialize chat connection and load history
   */
  const initializeChat = async () => {
    try {
      // Connect to WebSocket
      await chatService.connect({
        onMessage: handleIncomingMessage,
        onTyping: () => setIsTyping(true),
        onConnect: () => {
          setIsConnected(true)
          // Add welcome message
          setMessages([
            {
              id: 'welcome',
              role: 'assistant',
              content: "Hi! I'm your E-Com67 shopping assistant. How can I help you today? I can help you find products, answer questions, or assist with your orders.",
              timestamp: Date.now()
            }
          ])
        },
        onDisconnect: () => setIsConnected(false),
        onError: (error) => {
          console.error('Chat error:', error)
          setMessages(prev => [...prev, {
            id: `error-${Date.now()}`,
            role: 'system',
            content: 'Connection error. Please try again.',
            timestamp: Date.now()
          }])
        }
      })

      // Load chat history
      const history = await chatService.loadHistory()
      if (history && history.length > 0) {
        setMessages(prev => [...prev, ...history])
      }
    } catch (error) {
      console.error('Failed to initialize chat:', error)
    }
  }

  /**
   * Handle incoming messages from WebSocket
   * Backend sends: { type, message, timestamp, session_id, data }
   * We need to map to our internal format: { id, role, content, timestamp, metadata }
   */
  const handleIncomingMessage = (data) => {
    setIsTyping(false)

    // Map backend format to frontend format
    // Backend uses 'message' field, frontend uses 'content'
    // Backend doesn't send 'role', we infer it from message type
    const content = data.message || data.content || ''
    const role = data.role || (data.type === 'error' ? 'system' : 'assistant')

    setMessages(prev => [...prev, {
      id: data.messageId || `msg-${Date.now()}`,
      role: role,
      content: content,
      timestamp: data.timestamp || Date.now(),
      metadata: data.data || data.metadata  // Backend sends additional data in 'data' field
    }])
  }

  /**
   * Send message to AI assistant
   */
  const sendMessage = async (e) => {
    e.preventDefault()

    const trimmedMessage = inputMessage.trim()
    if (!trimmedMessage || isSending || !isConnected) return

    // Add user message to UI immediately
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmedMessage,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsSending(true)
    setIsTyping(true)

    try {
      // Send message through WebSocket
      await chatService.sendMessage(trimmedMessage)
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'system',
        content: 'Failed to send message. Please try again.',
        timestamp: Date.now()
      }])
      setIsTyping(false)
    } finally {
      setIsSending(false)
    }
  }

  /**
   * Scroll to bottom of message list
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * Toggle chat window
   */
  const toggleChat = () => {
    if (isOpen) {
      setIsOpen(false)
      setIsMinimized(false)
    } else {
      setIsOpen(true)
      setIsMinimized(false)
      // Focus input when opening
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  /**
   * Minimize chat window
   */
  const minimizeChat = () => {
    setIsMinimized(true)
  }

  /**
   * Restore minimized chat
   */
  const restoreChat = () => {
    setIsMinimized(false)
    setTimeout(() => inputRef.current?.focus(), 100)
  }

  /**
   * Format timestamp for display
   */
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  }

  /**
   * Render product recommendation if present in metadata
   */
  const renderProductRecommendation = (metadata) => {
    if (!metadata?.productReferences || metadata.productReferences.length === 0) {
      return null
    }

    return (
      <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md text-sm">
        <p className="text-blue-800 font-medium mb-1">Recommended Products:</p>
        {metadata.productReferences.map((productId, index) => (
          <a
            key={index}
            href={`/products/${productId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 underline block"
          >
            View Product
          </a>
        ))}
      </div>
    )
  }

  // Don't render if closed
  if (!isOpen) {
    return (
      <button
        onClick={toggleChat}
        className="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 z-50 flex items-center gap-2"
        aria-label="Open chat"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    )
  }

  // Minimized state
  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={restoreChat}
          className="bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg hover:bg-blue-700 transition-all duration-200 flex items-center gap-2"
        >
          <MessageCircle className="h-5 w-5" />
          <span className="font-medium">Chat Support</span>
          {messages.length > 1 && (
            <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
              {messages.length - 1}
            </span>
          )}
        </button>
      </div>
    )
  }

  // Full chat window
  return (
    <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-white rounded-lg shadow-2xl z-50 flex flex-col border border-gray-200">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 rounded-t-lg flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          <div>
            <h3 className="font-semibold">E-Com67 Support</h3>
            <p className="text-xs text-blue-100">
              {isConnected ? 'Online' : 'Connecting...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={minimizeChat}
            className="text-white hover:bg-blue-700 p-1 rounded transition-colors"
            aria-label="Minimize chat"
          >
            <Minimize2 className="h-5 w-5" />
          </button>
          <button
            onClick={toggleChat}
            className="text-white hover:bg-blue-700 p-1 rounded transition-colors"
            aria-label="Close chat"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.role === 'system'
                  ? 'bg-red-100 text-red-800 border border-red-200'
                  : 'bg-white text-gray-900 border border-gray-200'
              } rounded-lg p-3 shadow-sm`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {message.metadata && renderProductRecommendation(message.metadata)}
              <p
                className={`text-xs mt-1 ${
                  message.role === 'user'
                    ? 'text-blue-100'
                    : message.role === 'system'
                    ? 'text-red-600'
                    : 'text-gray-500'
                }`}
              >
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-4 border-t border-gray-200 bg-white rounded-b-lg">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected || isSending}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
          />
          <button
            type="submit"
            disabled={!isConnected || isSending || !inputMessage.trim()}
            className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            {isSending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatWidget
