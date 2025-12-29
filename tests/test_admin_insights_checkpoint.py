"""
Checkpoint tests for Admin Insights Agent core functionality.

This test suite validates:
1. Agent initialization
2. Tool invocation
3. Session memory
4. Core integration

These tests ensure the basic agent functionality works before proceeding
with more advanced features like guardrails and MCP gateway.
"""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Set environment variables before importing modules
os.environ['MEMORY_ID'] = 'test-memory-id'
os.environ['GUARDRAIL_ID'] = 'test-guardrail-id'
os.environ['MODEL_ID'] = 'amazon.nova-pro-v1:0'
os.environ['AWS_REGION'] = 'ap-southeast-1'
os.environ['ORDER_TRENDS_TOOL_ARN'] = 'arn:aws:lambda:ap-southeast-1:123456789012:function:order-trends'
os.environ['SALES_INSIGHTS_TOOL_ARN'] = 'arn:aws:lambda:ap-southeast-1:123456789012:function:sales-insights'
os.environ['PRODUCT_SEARCH_TOOL_ARN'] = 'arn:aws:lambda:ap-southeast-1:123456789012:function:product-search'
os.environ['ORDERS_TABLE_NAME'] = 'test-orders'
os.environ['PRODUCTS_TABLE_NAME'] = 'test-products'

# Add lambda directories to path
sys.path.insert(0, 'lambda/admin_insights_agent')
sys.path.insert(0, 'lambda/admin_insights_tools')


class TestAgentInitialization:
    """Test agent initialization functionality"""
    
    def test_initialize_agent_with_valid_parameters(self):
        """Test that agent initializes successfully with valid parameters"""
        import agent as agent_module
        
        # Mock Strands SDK components - need to mock the imports
        mock_strands = Mock()
        mock_strands.Agent = Mock()
        mock_strands.models.BedrockModel = Mock()
        mock_strands.agent.conversation_manager.SlidingWindowConversationManager = Mock()
        
        with patch.dict('sys.modules', {'strands': mock_strands, 
                                        'strands.models': mock_strands.models,
                                        'strands.agent': mock_strands.agent,
                                        'strands.agent.conversation_manager': mock_strands.agent.conversation_manager}):
            
            # Setup mocks
            mock_agent_instance = Mock()
            mock_strands.Agent.return_value = mock_agent_instance
            
            # Call initialize_agent
            result = agent_module.initialize_agent(
                session_id="test-session-123",
                actor_id="admin-user-456",
                memory_id="test-memory-id"
            )
            
            # Verify result structure
            assert result is not None
            assert result["session_id"] == "test-session-123"
            assert result["actor_id"] == "admin-user-456"
            assert result["memory_id"] == "test-memory-id"
            assert result["model_id"] == "amazon.nova-pro-v1:0"
            assert "agent" in result
            assert "tools" in result
            assert len(result["tools"]) == 3  # order_trends, sales_insights, product_search
            
            # Verify Agent was instantiated
            mock_strands.Agent.assert_called_once()
    
    def test_initialize_agent_missing_session_id(self):
        """Test that initialization fails without session_id"""
        import agent as agent_module
        
        with pytest.raises(ValueError, match="session_id is required"):
            agent_module.initialize_agent(
                session_id="",
                actor_id="admin-user-456",
                memory_id="test-memory-id"
            )
    
    def test_initialize_agent_missing_actor_id(self):
        """Test that initialization fails without actor_id"""
        import agent as agent_module
        
        with pytest.raises(ValueError, match="actor_id is required"):
            agent_module.initialize_agent(
                session_id="test-session-123",
                actor_id="",
                memory_id="test-memory-id"
            )
    
    def test_initialize_agent_missing_memory_id(self):
        """Test that initialization fails without memory_id"""
        import agent as agent_module
        
        with pytest.raises(ValueError, match="memory_id is required"):
            agent_module.initialize_agent(
                session_id="test-session-123",
                actor_id="admin-user-456",
                memory_id=""
            )
    
    def test_initialize_agent_tool_schemas(self):
        """Test that agent is initialized with correct tool schemas"""
        import agent as agent_module
        
        # Mock Strands SDK components
        mock_strands = Mock()
        mock_strands.Agent = Mock()
        mock_strands.models.BedrockModel = Mock()
        mock_strands.agent.conversation_manager.SlidingWindowConversationManager = Mock()
        
        with patch.dict('sys.modules', {'strands': mock_strands, 
                                        'strands.models': mock_strands.models,
                                        'strands.agent': mock_strands.agent,
                                        'strands.agent.conversation_manager': mock_strands.agent.conversation_manager}):
            
            mock_agent_instance = Mock()
            mock_strands.Agent.return_value = mock_agent_instance
            
            result = agent_module.initialize_agent(
                session_id="test-session-123",
                actor_id="admin-user-456",
                memory_id="test-memory-id"
            )
            
            # Verify tool names
            assert "order_trends" in result["tools"]
            assert "sales_insights" in result["tools"]
            assert "product_search" in result["tools"]


class TestToolInvocation:
    """Test tool invocation functionality"""
    
    def test_invoke_order_trends_tool(self):
        """Test invoking the order trends tool"""
        import agent as agent_module
        
        # Mock Lambda client
        with patch('agent.lambda_client') as mock_lambda:
            # Setup mock response
            mock_response = {
                'StatusCode': 200,
                'Payload': Mock(read=lambda: json.dumps({
                    'statusCode': 200,
                    'body': json.dumps({
                        'time_series': [],
                        'summary': {'total_orders': 10},
                        'status_breakdown': {'pending': 5, 'shipped': 5}
                    })
                }).encode())
            }
            mock_lambda.invoke.return_value = mock_response
            
            # Invoke tool
            result = agent_module.invoke_tool(
                tool_name="order_trends",
                tool_input={
                    "date_from": 1704067200,
                    "date_to": 1704153600,
                    "group_by": "day",
                    "metrics": ["volume", "revenue"]
                }
            )
            
            # Verify result
            assert result is not None
            assert 'time_series' in result
            assert 'summary' in result
            assert result['summary']['total_orders'] == 10
            
            # Verify Lambda was invoked
            mock_lambda.invoke.assert_called_once()
            call_args = mock_lambda.invoke.call_args
            assert call_args[1]['FunctionName'] == os.environ['ORDER_TRENDS_TOOL_ARN']
    
    def test_invoke_sales_insights_tool(self):
        """Test invoking the sales insights tool"""
        import agent as agent_module
        
        with patch('agent.lambda_client') as mock_lambda:
            mock_response = {
                'StatusCode': 200,
                'Payload': Mock(read=lambda: json.dumps({
                    'statusCode': 200,
                    'body': json.dumps({
                        'top_products': [],
                        'category_performance': {},
                        'low_performers': [],
                        'insights': [],
                        'summary': {'total_revenue': 1000.0}
                    })
                }).encode())
            }
            mock_lambda.invoke.return_value = mock_response
            
            result = agent_module.invoke_tool(
                tool_name="sales_insights",
                tool_input={
                    "date_from": 1704067200,
                    "date_to": 1704153600,
                    "sort_by": "revenue",
                    "limit": 10
                }
            )
            
            assert result is not None
            assert 'top_products' in result
            assert 'summary' in result
            assert result['summary']['total_revenue'] == 1000.0
    
    def test_invoke_product_search_tool(self):
        """Test invoking the product search tool"""
        import agent as agent_module
        
        with patch('agent.lambda_client') as mock_lambda:
            mock_response = {
                'StatusCode': 200,
                'Payload': Mock(read=lambda: json.dumps({
                    'statusCode': 200,
                    'body': json.dumps({
                        'products': [
                            {
                                'product_id': 'prod-123',
                                'name': 'Test Product',
                                'description': 'A test product',
                                'category': 'Electronics',
                                'price': 99.99,
                                'stock': 10,
                                'is_active': True,
                                'tags': []
                            }
                        ],
                        'total_results': 1,
                        'query': 'test',
                        'filters_applied': {}
                    })
                }).encode())
            }
            mock_lambda.invoke.return_value = mock_response
            
            result = agent_module.invoke_tool(
                tool_name="product_search",
                tool_input={
                    "query": "test",
                    "limit": 10
                }
            )
            
            assert result is not None
            assert 'products' in result
            assert len(result['products']) == 1
            assert result['products'][0]['name'] == 'Test Product'
    
    def test_invoke_unknown_tool(self):
        """Test that invoking unknown tool raises error"""
        import agent as agent_module
        
        with pytest.raises(ValueError, match="Unknown tool"):
            agent_module.invoke_tool(
                tool_name="unknown_tool",
                tool_input={}
            )
    
    def test_invoke_tool_without_arn(self):
        """Test that invoking tool without ARN raises error"""
        import agent as agent_module
        
        # Temporarily clear ARN
        original_arn = os.environ.get('ORDER_TRENDS_TOOL_ARN')
        
        try:
            # Clear the ARN and reload the module to pick up the change
            os.environ['ORDER_TRENDS_TOOL_ARN'] = ''
            import importlib
            importlib.reload(agent_module)
            
            with pytest.raises(RuntimeError, match="Tool ARN not configured"):
                agent_module.invoke_tool(
                    tool_name="order_trends",
                    tool_input={}
                )
        finally:
            # Restore ARN
            if original_arn:
                os.environ['ORDER_TRENDS_TOOL_ARN'] = original_arn
            else:
                os.environ['ORDER_TRENDS_TOOL_ARN'] = 'arn:aws:lambda:ap-southeast-1:123456789012:function:order-trends'
            # Reload to restore
            importlib.reload(agent_module)


class TestSessionMemory:
    """Test session memory functionality"""
    
    def test_create_session(self):
        """Test creating a new session"""
        import session_manager
        
        # Mock boto3 client
        with patch('session_manager.boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_client.create_event.return_value = {
                'eventId': 'event-123'
            }
            mock_boto_client.return_value = mock_client
            
            # Create session manager
            manager = session_manager.SessionManager(
                memory_id="test-memory-id",
                region="ap-southeast-1"
            )
            
            # Create session
            result = manager.create_session(
                actor_id="admin-user-456",
                session_id="test-session-123"
            )
            
            # Verify result
            assert result is not None
            assert result['session_id'] == "test-session-123"
            assert result['actor_id'] == "admin-user-456"
            assert result['memory_id'] == "test-memory-id"
            assert 'created_at' in result
            assert result['max_turns'] == 20
            
            # Verify create_event was called
            mock_client.create_event.assert_called_once()
    
    def test_get_session_history(self):
        """Test retrieving session history"""
        import session_manager
        
        with patch('session_manager.boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_client.list_events.return_value = {
                'events': [
                    {
                        'eventId': 'event-1',
                        'eventType': 'MESSAGE',
                        'eventData': {'role': 'USER', 'content': 'Hello'}
                    },
                    {
                        'eventId': 'event-2',
                        'eventType': 'MESSAGE',
                        'eventData': {'role': 'ASSISTANT', 'content': 'Hi there'}
                    }
                ]
            }
            mock_boto_client.return_value = mock_client
            
            manager = session_manager.SessionManager(memory_id="test-memory-id")
            
            result = manager.get_session_history(
                actor_id="admin-user-456",
                session_id="test-session-123"
            )
            
            assert result is not None
            assert result['session_id'] == "test-session-123"
            assert result['actor_id'] == "admin-user-456"
            assert len(result['events']) == 2
            assert result['events'][0]['eventType'] == 'MESSAGE'
    
    def test_terminate_session(self):
        """Test terminating a session"""
        import session_manager
        
        with patch('session_manager.boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_client.create_event.return_value = {
                'eventId': 'event-terminate'
            }
            mock_boto_client.return_value = mock_client
            
            manager = session_manager.SessionManager(memory_id="test-memory-id")
            
            result = manager.terminate_session(
                actor_id="admin-user-456",
                session_id="test-session-123"
            )
            
            assert result is not None
            assert result['session_id'] == "test-session-123"
            assert result['status'] == 'terminated'
            assert 'terminated_at' in result
    
    def test_store_message(self):
        """Test storing a message in session memory"""
        import session_manager
        
        with patch('session_manager.boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_client.create_event.return_value = {
                'eventId': 'event-msg-123'
            }
            mock_boto_client.return_value = mock_client
            
            manager = session_manager.SessionManager(memory_id="test-memory-id")
            
            result = manager.store_message(
                actor_id="admin-user-456",
                session_id="test-session-123",
                role="USER",
                content="What are my top selling products?"
            )
            
            assert result is not None
            assert result['session_id'] == "test-session-123"
            assert result['role'] == 'USER'
            assert 'stored_at' in result
    
    def test_session_manager_missing_memory_id(self):
        """Test that SessionManager requires memory_id"""
        import session_manager
        
        with pytest.raises(ValueError, match="memory_id is required"):
            session_manager.SessionManager(memory_id="")


class TestGuardrails:
    """Test guardrails functionality"""
    
    def test_apply_guardrails_no_violations(self):
        """Test applying guardrails with clean content"""
        import agent as agent_module
        
        with patch('agent.bedrock_runtime') as mock_bedrock:
            mock_bedrock.apply_guardrail.return_value = {
                'action': 'NONE',
                'outputs': [{'text': 'Clean content'}],
                'assessments': []
            }
            
            result = agent_module.apply_guardrails(
                content="What are my top selling products?",
                source="INPUT"
            )
            
            assert result['action'] == 'NONE'
            assert result['content'] == 'Clean content'
            assert len(result['violations']) == 0
    
    def test_apply_guardrails_pii_detected(self):
        """Test applying guardrails with PII content"""
        import agent as agent_module
        
        with patch('agent.bedrock_runtime') as mock_bedrock:
            mock_bedrock.apply_guardrail.return_value = {
                'action': 'BLOCKED',
                'outputs': [{'text': ''}],
                'assessments': [{
                    'sensitiveInformationPolicy': {
                        'piiEntities': [
                            {'type': 'EMAIL'}
                        ]
                    }
                }]
            }
            
            result = agent_module.apply_guardrails(
                content="Contact me at test@example.com",
                source="INPUT"
            )
            
            assert result['action'] == 'BLOCKED'
            assert len(result['violations']) > 0
            assert 'PII detected: EMAIL' in result['violations']
    
    def test_apply_guardrails_without_guardrail_id(self):
        """Test that guardrails are skipped when GUARDRAIL_ID is not set"""
        import agent as agent_module
        
        # Temporarily clear GUARDRAIL_ID
        original_id = os.environ.get('GUARDRAIL_ID')
        os.environ['GUARDRAIL_ID'] = ''
        
        try:
            # Reload the module to pick up the new environment variable
            import importlib
            importlib.reload(agent_module)
            
            result = agent_module.apply_guardrails(
                content="Test content",
                source="INPUT"
            )
            
            assert result['action'] == 'NONE'
            assert result['content'] == 'Test content'
            assert len(result['violations']) == 0
        finally:
            # Restore GUARDRAIL_ID
            if original_id:
                os.environ['GUARDRAIL_ID'] = original_id
            # Reload again to restore original state
            importlib.reload(agent_module)


class TestResponseFormatting:
    """Test response formatting functionality"""
    
    def test_format_response_with_metadata(self):
        """Test formatting response with metadata"""
        import agent as agent_module
        
        processing_result = {
            "response": "Your top selling product is Product A with $1000 in revenue.",
            "session_id": "test-session-123",
            "actor_id": "admin-user-456",
            "tools_invoked": ["sales_insights"],
            "timestamp": 1704067200
        }
        
        result = agent_module.format_response(
            processing_result=processing_result,
            include_metadata=True
        )
        
        assert result['response'] == processing_result['response']
        assert result['session_id'] == "test-session-123"
        assert result['timestamp'] == 1704067200
        assert 'metadata' in result
        assert result['metadata']['actor_id'] == "admin-user-456"
        assert result['metadata']['tools_invoked'] == ["sales_insights"]
        assert result['metadata']['tools_count'] == 1
    
    def test_format_response_without_metadata(self):
        """Test formatting response without metadata"""
        import agent as agent_module
        
        processing_result = {
            "response": "Test response",
            "session_id": "test-session-123",
            "actor_id": "admin-user-456",
            "tools_invoked": [],
            "timestamp": 1704067200
        }
        
        result = agent_module.format_response(
            processing_result=processing_result,
            include_metadata=False
        )
        
        assert result['response'] == "Test response"
        assert result['session_id'] == "test-session-123"
        assert result['timestamp'] == 1704067200
        assert 'metadata' not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
