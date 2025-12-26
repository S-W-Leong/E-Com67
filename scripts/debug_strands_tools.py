#!/usr/bin/env python3
"""
Debug script to test Strands agent tool configuration
"""

import os
import sys
import json
from unittest.mock import MagicMock, patch

# Set up environment variables
os.environ.update({
    'CHAT_HISTORY_TABLE_NAME': 'test-chat-history',
    'PRODUCTS_TABLE_NAME': 'test-products',
    'OPENSEARCH_ENDPOINT': 'https://test-opensearch.amazonaws.com',
    'AWS_REGION': 'ap-southeast-1',
    'DEPLOYMENT_STAGE': 'development',
    'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1',
    'BEDROCK_TEMPERATURE': '0.7',
    'BEDROCK_MAX_TOKENS': '4096',
    'BEDROCK_STREAMING': 'false',
    'PLATFORM_VERSION': '1.0.0'
})

# Add lambda/chat to path
sys.path.insert(0, 'lambda/chat')

def test_strands_import():
    """Test if Strands SDK can be imported"""
    print("1. Testing Strands SDK import...")
    try:
        # Mock strands for local testing
        strands_mock = MagicMock()
        strands_mock.Agent = MagicMock()
        strands_mock.tool = lambda func: func  # Simple decorator mock
        sys.modules['strands'] = strands_mock
        sys.modules['strands.models'] = MagicMock()
        sys.modules['strands.agent'] = MagicMock()
        sys.modules['strands.agent.conversation_manager'] = MagicMock()
        
        from strands_config import StrandsAgentManager, StrandsAgentConfig
        print("   ✓ Strands configuration imported successfully")
        
        config = StrandsAgentConfig.from_environment()
        print(f"   ✓ Configuration created: {config.platform_name}")
        
        return True
    except Exception as e:
        print(f"   ✗ Strands import failed: {e}")
        return False

def test_tool_imports():
    """Test if tools can be imported"""
    print("\n2. Testing tool imports...")
    
    # Mock dependencies
    sys.modules['opensearchpy'] = MagicMock()
    sys.modules['pydantic'] = MagicMock()
    
    # Mock pydantic BaseModel
    class MockBaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self, **kwargs):
            return {}
    
    sys.modules['pydantic'].BaseModel = MockBaseModel
    sys.modules['pydantic'].Field = lambda **kwargs: None
    
    try:
        # Test models import
        from models import ProductInfo, ProductSearchResponse
        print("   ✓ Models imported successfully")
        
        # Test tool imports
        from tools.product_search_tool import product_search, get_product_details
        print("   ✓ Product search tools imported")
        
        from tools.cart_management_tool import add_to_cart, get_cart_contents
        print("   ✓ Cart management tools imported")
        
        from tools.order_query_tool import get_order_history
        print("   ✓ Order query tools imported")
        
        from tools.knowledge_base_tool import search_knowledge_base
        print("   ✓ Knowledge base tools imported")
        
        return True
    except Exception as e:
        print(f"   ✗ Tool import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_creation():
    """Test agent creation with tools"""
    print("\n3. Testing agent creation...")
    
    try:
        from strands_config import StrandsAgentManager
        
        # Create agent manager
        manager = StrandsAgentManager()
        print("   ✓ Agent manager created")
        
        # Test tool loading
        user_context = {'user_id': 'test', 'session_id': 'test'}
        tools = manager._get_custom_tools(user_context)
        print(f"   ✓ Tools loaded: {len(tools)} tools")
        
        # List tool names
        tool_names = []
        for tool in tools:
            if hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        
        print(f"   Tool names: {tool_names}")
        
        return True
    except Exception as e:
        print(f"   ✗ Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_decoration():
    """Test if @tool decorator is working"""
    print("\n4. Testing tool decoration...")
    
    try:
        from tools.product_search_tool import product_search
        
        # Check if function has tool attributes
        print(f"   Function: {product_search}")
        print(f"   Function name: {getattr(product_search, '__name__', 'unknown')}")
        print(f"   Function doc: {getattr(product_search, '__doc__', 'no doc')[:100]}...")
        
        # Check if it's callable
        if callable(product_search):
            print("   ✓ Function is callable")
        else:
            print("   ✗ Function is not callable")
        
        return True
    except Exception as e:
        print(f"   ✗ Tool decoration test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("Strands Agent Tool Diagnostic")
    print("=" * 50)
    
    results = {
        'strands_import': test_strands_import(),
        'tool_imports': test_tool_imports(),
        'agent_creation': test_agent_creation(),
        'tool_decoration': test_tool_decoration()
    }
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Tools should be working.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Tools may not work properly.")
        
        print("\nPOSSIBLE ISSUES:")
        if not results['strands_import']:
            print("- Strands SDK not properly installed in Lambda layer")
        if not results['tool_imports']:
            print("- Missing dependencies (pydantic, opensearchpy, etc.)")
        if not results['agent_creation']:
            print("- Agent configuration or tool registration issue")
        if not results['tool_decoration']:
            print("- @tool decorator not working properly")

if __name__ == '__main__':
    main()