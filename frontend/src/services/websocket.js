// WebSocket service for AI Chat
class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
  }

  connect(userId, onMessage, onError) {
    // For now, using mock WebSocket
    // Replace with actual WebSocket URL from API Gateway when ready
    const wsUrl = `wss://your-websocket-url.execute-api.${import.meta.env.VITE_AWS_REGION}.amazonaws.com/prod`;

    console.log('WebSocket connection would connect to:', wsUrl);
    console.log('Mock WebSocket service active for userId:', userId);

    // Store callbacks
    this.listeners.set('message', onMessage);
    this.listeners.set('error', onError);

    // Mock connection success
    setTimeout(() => {
      if (this.listeners.has('message')) {
        this.listeners.get('message')({
          type: 'system',
          message: 'Connected to AI Assistant (Mock Mode)',
          timestamp: Date.now(),
        });
      }
    }, 500);

    return true;
  }

  sendMessage(message) {
    console.log('Sending message:', message);

    // Mock response
    setTimeout(() => {
      if (this.listeners.has('message')) {
        this.listeners.get('message')({
          type: 'assistant',
          message: this.generateMockResponse(message),
          timestamp: Date.now(),
        });
      }
    }, 1000);
  }

  generateMockResponse(userMessage) {
    const responses = {
      hello: "Hello! I'm your AI shopping assistant. How can I help you today?",
      help: "I can help you find products, answer questions about items, and provide recommendations. What are you looking for?",
      product: "I can help you find products. What category are you interested in? We have Electronics, Clothing, Books, and Home items.",
      price: "I can help you find products within your budget. What's your price range?",
      recommend: "Based on popular items, I'd recommend checking out our Electronics section. We have great deals on laptops and smartphones!",
    };

    const lowerMessage = userMessage.toLowerCase();

    for (const [key, response] of Object.entries(responses)) {
      if (lowerMessage.includes(key)) {
        return response;
      }
    }

    return `I understand you said: "${userMessage}". I'm currently in demo mode. In production, I would provide personalized product recommendations using AWS Bedrock!`;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
    console.log('WebSocket disconnected');
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export default new WebSocketService();
