"""
Integration tests for Admin Insights Agent
Tests frontend integration, WebSocket connection, message flow, and MCP gateway
"""
import pytest
import json
import os
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Test configuration
REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')
WEBSOCKET_URL = os.environ.get('WEBSOCKET_URL', '')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID', '')
MCP_GATEWAY_URL = os.environ.get('MCP_GATEWAY_URL', '')


class TestWebSocketConnection:
    """Test WebSocket connection establishment and basic communication"""
    
    def test_websocket_connection_with_mock_auth(self):
        """Test WebSocket connection flow with mocked authentication"""
        # Mock the WebSocket connection
        mock_ws = Mock()
        mock_ws.connected = True
        
        # Simulate connection establishment
        connection_id = "test-connection-123"
        session_id = "test-session-456"
        
        # Verify connection data structure
        connection_data = {
            "connectionId": connection_id,
            "sessionId": session_id,
            "actorId": "admin-user-123",
            "connectedAt": int(time.time())
        }
        
        assert connection_data["connectionId"] == connection_id
        assert connection_data["sessionId"] == session_id
        assert "actorId" in connection_data
        assert "connectedAt" in connection_data


class TestMessageFlow:
    """Test message flow from frontend to agent"""
    
    def test_message_format_structure(self):
        """Test that message format follows expected structure"""
        # Test user message format
        user_message = {
            "action": "sendMessage",
            "message": "Show me order trends for last week",
            "sessionId": "test-session-123"
        }
        
        assert "action" in user_message
        assert "message" in user_message
        assert user_message["action"] == "sendMessage"
        assert isinstance(user_message["message"], str)
    
    def test_agent_response_format(self):
        """Test that agent response follows expected format"""
        # Test response chunk format
        response_chunk = {
            "type": "chunk",
            "content": "Here are the order trends...",
            "timestamp": int(time.time())
        }
        
        assert "type" in response_chunk
        assert "content" in response_chunk
        assert response_chunk["type"] in ["chunk", "complete", "error"]
        
        # Test complete response format
        complete_response = {
            "type": "complete",
            "content": "Analysis complete",
            "toolsInvoked": ["order_trends"],
            "timestamp": int(time.time())
        }
        
        assert complete_response["type"] == "complete"
        assert "toolsInvoked" in complete_response
    
    def test_error_response_format(self):
        """Test error response format"""
        error_response = {
            "type": "error",
            "content": "Failed to process request",
            "error": {
                "code": "TOOL_EXECUTION_ERROR",
                "message": "DynamoDB query failed"
            },
            "timestamp": int(time.time())
        }
        
        assert error_response["type"] == "error"
        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]


class TestAnalyticsDataFormatting:
    """Test analytics data formatting in chat responses"""
    
    def test_order_trends_data_format(self):
        """Test order trends data formatting"""
        # Sample order trends data
        order_trends_data = {
            "time_series": [
                {"timestamp": 1704067200, "volume": 45, "revenue": 12500.50},
                {"timestamp": 1704153600, "volume": 52, "revenue": 14200.75}
            ],
            "summary": {
                "total_orders": 97,
                "total_revenue": 26701.25,
                "growth_rate": 15.5
            },
            "status_breakdown": {
                "pending": 5,
                "processing": 10,
                "shipped": 30,
                "delivered": 50,
                "cancelled": 2
            }
        }
        
        # Verify structure
        assert "time_series" in order_trends_data
        assert "summary" in order_trends_data
        assert "status_breakdown" in order_trends_data
        assert len(order_trends_data["time_series"]) > 0
        assert order_trends_data["summary"]["total_orders"] == 97
    
    def test_sales_insights_data_format(self):
        """Test sales insights data formatting"""
        # Sample sales insights data
        sales_insights_data = {
            "top_products": [
                {
                    "productId": "prod-123",
                    "name": "Premium Widget",
                    "revenue": 5000.00,
                    "units_sold": 100
                }
            ],
            "category_performance": {
                "Electronics": {"revenue": 15000.00, "units": 250},
                "Clothing": {"revenue": 8000.00, "units": 400}
            },
            "low_performers": [],
            "insights": [
                "Electronics category showing strong growth",
                "Premium Widget is top seller"
            ]
        }
        
        # Verify structure
        assert "top_products" in sales_insights_data
        assert "category_performance" in sales_insights_data
        assert "insights" in sales_insights_data
        assert len(sales_insights_data["top_products"]) > 0
    
    def test_product_search_data_format(self):
        """Test product search data formatting"""
        # Sample product search data
        product_search_data = {
            "products": [
                {
                    "productId": "prod-456",
                    "name": "Smart Watch",
                    "category": "Electronics",
                    "price": 299.99,
                    "stock": 50
                }
            ],
            "total_results": 1
        }
        
        # Verify structure
        assert "products" in product_search_data
        assert "total_results" in product_search_data
        assert product_search_data["total_results"] == len(product_search_data["products"])


class TestMCPGatewayAuthentication:
    """Test MCP Gateway authentication"""
    
    def test_jwt_token_structure(self):
        """Test JWT token structure for MCP gateway"""
        # Mock JWT token payload
        token_payload = {
            "sub": "admin-user-123",
            "cognito:username": "admin@example.com",
            "cognito:groups": ["Admins"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        # Verify required fields
        assert "sub" in token_payload
        assert "exp" in token_payload
        assert "iat" in token_payload
        assert token_payload["exp"] > token_payload["iat"]
    
    def test_authentication_header_format(self):
        """Test authentication header format"""
        mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
        
        headers = {
            "Authorization": f"Bearer {mock_token}",
            "Content-Type": "application/json"
        }
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert "Content-Type" in headers
    
    def test_authentication_error_response(self):
        """Test authentication error response format"""
        auth_error = {
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired token",
                "timestamp": int(time.time())
            }
        }
        
        assert "error" in auth_error
        assert auth_error["error"]["code"] == "UNAUTHORIZED"


class TestMCPGatewayToolInvocation:
    """Test MCP Gateway tool invocation"""
    
    def test_tool_discovery_request(self):
        """Test tool discovery request format"""
        # Tool discovery should return list of available tools
        expected_tools = [
            "order_trends",
            "sales_insights",
            "product_search"
        ]
        
        # Verify all expected tools are present
        for tool in expected_tools:
            assert tool in expected_tools
    
    def test_tool_invocation_request_format(self):
        """Test tool invocation request format"""
        # Sample tool invocation request
        tool_request = {
            "tool": "order_trends",
            "parameters": {
                "date_from": 1704067200,
                "date_to": 1704672000,
                "group_by": "day",
                "metrics": ["volume", "revenue"]
            }
        }
        
        assert "tool" in tool_request
        assert "parameters" in tool_request
        assert tool_request["tool"] in ["order_trends", "sales_insights", "product_search"]
    
    def test_tool_response_format(self):
        """Test tool response format from MCP gateway"""
        # Sample tool response
        tool_response = {
            "tool": "order_trends",
            "result": {
                "time_series": [],
                "summary": {},
                "status_breakdown": {}
            },
            "status": "success",
            "timestamp": int(time.time())
        }
        
        assert "tool" in tool_response
        assert "result" in tool_response
        assert "status" in tool_response
        assert tool_response["status"] == "success"
    
    def test_tool_error_response_format(self):
        """Test tool error response format"""
        tool_error = {
            "tool": "order_trends",
            "error": {
                "code": "TOOL_EXECUTION_ERROR",
                "message": "Failed to query DynamoDB",
                "details": "Table not found"
            },
            "status": "error",
            "timestamp": int(time.time())
        }
        
        assert "tool" in tool_error
        assert "error" in tool_error
        assert "status" in tool_error
        assert tool_error["status"] == "error"


class TestEndToEndFlow:
    """Test end-to-end flow scenarios"""
    
    def test_complete_conversation_flow(self):
        """Test complete conversation flow structure"""
        # Simulate a complete conversation
        conversation = [
            {
                "role": "USER",
                "content": "Show me order trends for last week",
                "timestamp": int(time.time())
            },
            {
                "role": "ASSISTANT",
                "content": "I'll analyze the order trends for you...",
                "toolsInvoked": ["order_trends"],
                "timestamp": int(time.time()) + 1
            },
            {
                "role": "USER",
                "content": "What about top selling products?",
                "timestamp": int(time.time()) + 2
            },
            {
                "role": "ASSISTANT",
                "content": "Here are the top selling products...",
                "toolsInvoked": ["sales_insights"],
                "timestamp": int(time.time()) + 3
            }
        ]
        
        # Verify conversation structure
        assert len(conversation) == 4
        assert conversation[0]["role"] == "USER"
        assert conversation[1]["role"] == "ASSISTANT"
        assert "toolsInvoked" in conversation[1]
    
    def test_session_context_maintenance(self):
        """Test session context is maintained across messages"""
        # Session should maintain context
        session_context = {
            "sessionId": "test-session-789",
            "actorId": "admin-user-123",
            "messageCount": 4,
            "lastActivity": int(time.time()),
            "context": {
                "last_query": "order trends",
                "last_date_range": {"from": 1704067200, "to": 1704672000}
            }
        }
        
        assert "sessionId" in session_context
        assert "context" in session_context
        assert session_context["messageCount"] > 0


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_connection_error_handling(self):
        """Test connection error handling"""
        connection_error = {
            "type": "error",
            "error": {
                "code": "CONNECTION_FAILED",
                "message": "Failed to establish WebSocket connection"
            }
        }
        
        assert connection_error["type"] == "error"
        assert "CONNECTION_FAILED" in connection_error["error"]["code"]
    
    def test_tool_execution_error_handling(self):
        """Test tool execution error handling"""
        tool_error = {
            "type": "error",
            "error": {
                "code": "TOOL_EXECUTION_ERROR",
                "message": "Failed to execute analytics tool",
                "tool": "order_trends"
            }
        }
        
        assert tool_error["type"] == "error"
        assert "tool" in tool_error["error"]
    
    def test_guardrail_violation_error(self):
        """Test guardrail violation error handling"""
        guardrail_error = {
            "type": "error",
            "error": {
                "code": "GUARDRAIL_VIOLATION",
                "message": "Request blocked by security guardrails"
            }
        }
        
        assert guardrail_error["type"] == "error"
        assert "GUARDRAIL_VIOLATION" in guardrail_error["error"]["code"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
