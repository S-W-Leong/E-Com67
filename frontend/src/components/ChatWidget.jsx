import { useState, useEffect, useRef } from 'react';
import { getCurrentUser } from 'aws-amplify/auth';
import websocketService from '../services/websocket';

function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen && !isConnected) {
      connectWebSocket();
    }

    return () => {
      if (isConnected) {
        websocketService.disconnect();
      }
    };
  }, [isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const connectWebSocket = async () => {
    try {
      const user = await getCurrentUser();
      const userId = user.userId || user.username;

      websocketService.connect(
        userId,
        handleIncomingMessage,
        handleError
      );

      setIsConnected(true);
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  };

  const handleIncomingMessage = (message) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleError = (error) => {
    console.error('WebSocket error:', error);
    setMessages((prev) => [
      ...prev,
      {
        type: 'error',
        message: 'Connection error occurred',
        timestamp: Date.now(),
      },
    ]);
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMessage = {
      type: 'user',
      message: inputMessage,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    websocketService.sendMessage(inputMessage);
    setInputMessage('');
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </button>
      ) : (
        <div className="bg-white rounded-lg shadow-2xl w-96 h-[500px] flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-t-lg flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
              <h3 className="font-bold">AI Shopping Assistant</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="hover:bg-white/20 p-1 rounded"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                <p>👋 Hi! I'm your AI shopping assistant.</p>
                <p className="text-sm mt-2">How can I help you today?</p>
              </div>
            )}

            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    msg.type === 'user'
                      ? 'bg-blue-600 text-white'
                      : msg.type === 'error'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-white text-gray-800 shadow'
                  }`}
                >
                  <p className="text-sm">{msg.message}</p>
                  <p className="text-xs opacity-70 mt-1">{formatTime(msg.timestamp)}</p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSendMessage} className="p-4 border-t">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default ChatWidget;
