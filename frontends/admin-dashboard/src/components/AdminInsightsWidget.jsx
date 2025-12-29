/**
 * Admin Insights Chat Widget
 * 
 * Floating chat widget for conversational analytics with the Admin Insights Agent.
 * Provides real-time insights into orders, sales, and product performance through
 * natural language queries.
 * 
 * Features:
 * - Floating button in bottom-right corner
 * - Expandable chat window
 * - Real-time message streaming
 * - Connection status indicator
 * - Typing indicators
 * - Session persistence
 * 
 * Requirements: 1.1, 1.4
 */

import React, { useState, useEffect, useRef } from 'react'
import { MessageCircle, X, Send, Minimize2, AlertCircle, Loader2 } from 'lucide-react'
import adminInsightsService from '../services/adminInsights'
import { AnalyticsMessageFormatter } from './AnalyticsMessageFormatter'

const AdminInsightsWidget = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('')
  const [error, setError] = useState(null)
  
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Initialize connection and event handlers
  useEffect(() => {
    // Connection status handler
    const unsubscribeConnection = adminInsightsService.onConnectionChange((connected) => {
      setIsConnected(connected)
      setIsConnecting(false)
      
      if (connected) {
        setError(null)
        // Add welcome message on first connection
        if (messages.length === 0) {
          setMessages([{
            id: 'welcome',
            type: 'assistant',
            content: 'Hello! I\'m your Admin Insights Assistant. I can help you analyze orders, sales trends, and product performance. What would you like to know?',
            timestamp: Date.now()
          }])
        }
      }
    })

    // Message handler
    const unsubscribeMessage = adminInsightsService.onMessage((message) => {
      if (message.type === 'chunk') {
        // Streaming chunk - append to current message
        setCurrentStreamingMessage(prev => prev + message.content)
        setIsTyping(true)
      } else if (message.type === 'complete') {
        // Complete message - add to messages list
        const fullContent = currentStreamingMessage + message.content
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          type: 'assistant',
          content: fullContent,
          timestamp: Date.now()
        }])
        setCurrentStreamingMessage('')
        setIsTyping(false)
      } else if (message.type === 'error') {
        // Error message
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          type: 'error',
          content: message.content || 'An error occurred processing your request.',
          timestamp: Date.now()
        }])
        setCurrentStreamingMessage('')
        setIsTyping(false)
      }
    })

    // Error handler
    const unsubscribeError = adminInsightsService.onError((err) => {
      setError(err.message || 'Connection error')
      setIsConnecting(false)
    })

    // Connect when widget opens
    if (isOpen && !isConnected && !isConnecting) {
      setIsConnecting(true)
      adminInsightsService.connect()
    }

    // Cleanup
    return () => {
      unsubscribeConnection()
      unsubscribeMessage()
      unsubscribeError()
    }
  }, [isOpen, isConnected, isConnecting, currentStreamingMessage, messages.length])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentStreamingMessage])

  // Focus input when widget opens
  useEffect(() => {
    if (isOpen && isConnected) {
      inputRef.current?.focus()
    }
  }, [isOpen, isConnected])

  const handleToggle = () => {
    setIsOpen(!isOpen)
  }

  const handleMinimize = () => {
    setIsOpen(false)
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!inputValue.trim() || !isConnected) {
      return
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    }

    // Add user message to UI
    setMessages(prev => [...prev, userMessage])
    
    // Clear input
    setInputValue('')
    
    // Send to agent
    try {
      await adminInsightsService.sendMessage(userMessage.content)
      setIsTyping(true)
    } catch (error) {
      console.error('Failed to send message:', error)
      setError('Failed to send message')
    }
  }

  const handleClearSession = () => {
    if (window.confirm('Are you sure you want to start a new conversation? This will clear the current session.')) {
      adminInsightsService.clearSession()
      setMessages([{
        id: 'welcome-new',
        type: 'assistant',
        content: 'New session started. How can I help you today?',
        timestamp: Date.now()
      }])
      setCurrentStreamingMessage('')
      setIsTyping(false)
    }
  }

  const renderMessage = (message) => {
    const isUser = message.type === 'user'
    const isError = message.type === 'error'

    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`max-w-[80%] rounded-lg px-4 py-2 ${
            isUser
              ? 'bg-primary-600 text-white'
              : isError
              ? 'bg-red-50 text-red-900 border border-red-200'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          {isError && (
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="h-4 w-4" />
              <span className="text-xs font-semibold">Error</span>
            </div>
          )}
          {/* Use analytics formatter for assistant messages */}
          {!isUser && !isError ? (
            <AnalyticsMessageFormatter content={message.content} />
          ) : (
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          )}
          <div className={`text-xs mt-1 ${isUser ? 'text-primary-100' : 'text-gray-500'}`}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    )
  }

  const renderConnectionStatus = () => {
    if (isConnecting) {
      return (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Connecting...</span>
        </div>
      )
    }

    if (!isConnected) {
      return (
        <div className="flex items-center gap-2 text-xs text-red-600">
          <div className="h-2 w-2 rounded-full bg-red-600" />
          <span>Disconnected</span>
        </div>
      )
    }

    return (
      <div className="flex items-center gap-2 text-xs text-green-600">
        <div className="h-2 w-2 rounded-full bg-green-600 animate-pulse" />
        <span>Connected</span>
      </div>
    )
  }

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={handleToggle}
          className="fixed bottom-6 right-6 z-50 bg-primary-600 hover:bg-primary-700 text-white rounded-full p-4 shadow-lg transition-all duration-200 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          aria-label="Open Admin Insights Chat"
        >
          <MessageCircle className="h-6 w-6" />
          {!isConnected && (
            <div className="absolute top-0 right-0 h-3 w-3 bg-red-500 rounded-full border-2 border-white" />
          )}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-white rounded-lg shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          {/* Header */}
          <div className="bg-primary-600 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MessageCircle className="h-5 w-5" />
              <div>
                <h3 className="font-semibold text-sm">Admin Insights</h3>
                {renderConnectionStatus()}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleMinimize}
                className="hover:bg-primary-700 rounded p-1 transition-colors"
                aria-label="Minimize"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
              <button
                onClick={handleToggle}
                className="hover:bg-primary-700 rounded p-1 transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2 text-red-800 text-sm">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
            {messages.map(renderMessage)}
            
            {/* Streaming message */}
            {currentStreamingMessage && (
              <div className="flex justify-start mb-4">
                <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900">
                  <div className="text-sm whitespace-pre-wrap">{currentStreamingMessage}</div>
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {isTyping && !currentStreamingMessage && (
              <div className="flex justify-start mb-4">
                <div className="bg-gray-100 rounded-lg px-4 py-3">
                  <div className="flex gap-1">
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="h-2 w-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-4 bg-white">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={isConnected ? "Ask about orders, sales, products..." : "Connecting..."}
                disabled={!isConnected}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
              />
              <button
                type="submit"
                disabled={!isConnected || !inputValue.trim()}
                className="bg-primary-600 hover:bg-primary-700 text-white rounded-lg px-4 py-2 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            
            {/* Actions */}
            <div className="mt-2 flex justify-between items-center">
              <button
                onClick={handleClearSession}
                className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
              >
                Clear session
              </button>
              <span className="text-xs text-gray-400">
                Powered by Amazon Nova
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default AdminInsightsWidget
