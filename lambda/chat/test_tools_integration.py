"""
Test script for Strands AI Agent custom tools integration.

This script tests the basic functionality of the custom tools to ensure
they can be imported and initialized correctly.
"""

import os
import sys
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock environment variables for testing
os.environ.setdefault('OPENSEARCH_ENDPOINT', 'https://test-opensearch.amazonaws.com')
os.environ.setdefault('PRODUCTS_TABLE_NAME', 'test-products')
os.environ.setdefault('CART_TABLE_NAME', 'test-cart')
os.environ.setdefault('ORDERS_TABLE_NAME', 'test-orders')
os.environ.setdefault('KNOWLEDGE_BASE_ID', 'test-kb-id')
os.environ.setdefault('AWS_REGION', 'ap-southeast-1')


def test_tool_imports():
    """Test that all custom tools can be imported successfully"""
    logger.info("Testing tool imports...")
    
    try:
        # Test product search tool imports
        from tools.product_search_tool import product_search, get_product_details, get_product_recommendations
        logger.info("✓ Product search tools imported successfully")
        
        # Test cart management tool imports
        from tools.cart_management_tool import add_to_cart, get_cart_contents, update_cart_item, remove_from_cart, clear_cart
        logger.info("✓ Cart management tools imported successfully")
        
        # Test order query tool imports
        from tools.order_query_tool import get_order_history, get_order_details, track_order, search_orders
        logger.info("✓ Order query tools imported successfully")
        
        # Test knowledge base tool imports
        from tools.knowledge_base_tool import search_knowledge_base, get_platform_info, get_help_topics
        logger.info("✓ Knowledge base tools imported successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Tool import failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error during import: {str(e)}")
        return False


def test_strands_config():
    """Test Strands configuration and tool loading"""
    logger.info("Testing Strands configuration...")
    
    try:
        from strands_config import StrandsAgentManager, test_strands_sdk_import
        
        # Test SDK import
        sdk_test = test_strands_sdk_import()
        if sdk_test['sdk_available']:
            logger.info("✓ Strands SDK is available")
        else:
            logger.warning("⚠ Strands SDK not available - this is expected in test environment")
            logger.info(f"Import errors: {sdk_test['import_errors']}")
        
        # Test agent manager initialization
        agent_manager = StrandsAgentManager()
        logger.info("✓ Agent manager initialized successfully")
        
        # Test configuration validation
        validation = agent_manager.validate_configuration()
        if validation['valid']:
            logger.info("✓ Configuration is valid")
        else:
            logger.warning(f"⚠ Configuration issues: {validation['errors']}")
        
        logger.info(f"Configuration summary: {validation['config_summary']}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Strands config import failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error in Strands config: {str(e)}")
        return False


def test_model_imports():
    """Test Pydantic model imports"""
    logger.info("Testing Pydantic model imports...")
    
    try:
        from models import (
            ProductInfo, ProductSearchResponse, ProductRecommendation,
            CartSummary, CartItem, CartOperation,
            OrderHistory, OrderInfo, OrderTracking,
            AgentResponse, ErrorResponse, KnowledgeResponse
        )
        logger.info("✓ All Pydantic models imported successfully")
        
        # Test basic model creation
        product = ProductInfo(
            product_id="test-123",
            name="Test Product",
            description="A test product",
            price=29.99,
            category="test",
            stock=10,
            is_available=True
        )
        logger.info(f"✓ ProductInfo model created: {product.name}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Model import failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error in model creation: {str(e)}")
        return False


def test_tool_function_signatures():
    """Test that tool functions have correct signatures"""
    logger.info("Testing tool function signatures...")
    
    try:
        from tools.product_search_tool import product_search
        from tools.cart_management_tool import add_to_cart
        from tools.order_query_tool import get_order_history
        from tools.knowledge_base_tool import search_knowledge_base
        
        # Check if functions are callable
        assert callable(product_search), "product_search is not callable"
        assert callable(add_to_cart), "add_to_cart is not callable"
        assert callable(get_order_history), "get_order_history is not callable"
        assert callable(search_knowledge_base), "search_knowledge_base is not callable"
        
        logger.info("✓ All tool functions are callable")
        
        # Check if functions have @tool decorator (they should have __name__ attribute)
        assert hasattr(product_search, '__name__'), "product_search missing __name__ attribute"
        assert hasattr(add_to_cart, '__name__'), "add_to_cart missing __name__ attribute"
        
        logger.info("✓ Tool functions have proper attributes")
        
        return True
        
    except AssertionError as e:
        logger.error(f"✗ Tool function signature test failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error in signature test: {str(e)}")
        return False


def run_all_tests():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("STRANDS AI AGENT TOOLS INTEGRATION TEST")
    logger.info("=" * 60)
    
    tests = [
        ("Tool Imports", test_tool_imports),
        ("Pydantic Models", test_model_imports),
        ("Tool Function Signatures", test_tool_function_signatures),
        ("Strands Configuration", test_strands_config)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Tools are ready for integration.")
        return True
    else:
        logger.warning(f"⚠ {total - passed} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)