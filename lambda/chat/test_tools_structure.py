"""
Simple structure test for Strands AI Agent custom tools.

This script tests the basic structure and imports without requiring
external dependencies like opensearchpy or strands SDK.
"""

import os
import sys
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_file_structure():
    """Test that all required files exist"""
    logger.info("Testing file structure...")
    
    required_files = [
        'tools/__init__.py',
        'tools/product_search_tool.py',
        'tools/cart_management_tool.py', 
        'tools/order_query_tool.py',
        'tools/knowledge_base_tool.py',
        'models.py',
        'strands_config.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"✗ Missing files: {missing_files}")
        return False
    else:
        logger.info("✓ All required files exist")
        return True


def test_basic_imports():
    """Test basic Python imports without external dependencies"""
    logger.info("Testing basic imports...")
    
    try:
        # Test that files can be parsed as Python modules
        import ast
        
        files_to_check = [
            'tools/product_search_tool.py',
            'tools/cart_management_tool.py',
            'tools/order_query_tool.py', 
            'tools/knowledge_base_tool.py',
            'models.py',
            'strands_config.py'
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()
            
            try:
                ast.parse(content)
                logger.info(f"✓ {file_path} - valid Python syntax")
            except SyntaxError as e:
                logger.error(f"✗ {file_path} - syntax error: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Basic import test failed: {str(e)}")
        return False


def test_tool_function_definitions():
    """Test that tool functions are properly defined"""
    logger.info("Testing tool function definitions...")
    
    try:
        import ast
        
        # Expected tool functions in each file
        expected_functions = {
            'tools/product_search_tool.py': ['product_search', 'get_product_details', 'get_product_recommendations'],
            'tools/cart_management_tool.py': ['add_to_cart', 'get_cart_contents', 'update_cart_item', 'remove_from_cart', 'clear_cart'],
            'tools/order_query_tool.py': ['get_order_history', 'get_order_details', 'track_order', 'search_orders'],
            'tools/knowledge_base_tool.py': ['search_knowledge_base', 'get_platform_info', 'get_help_topics']
        }
        
        for file_path, expected_funcs in expected_functions.items():
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find function definitions
            function_names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_names.append(node.name)
            
            # Check for expected functions
            missing_functions = []
            for func_name in expected_funcs:
                if func_name not in function_names:
                    missing_functions.append(func_name)
            
            if missing_functions:
                logger.error(f"✗ {file_path} - missing functions: {missing_functions}")
                return False
            else:
                logger.info(f"✓ {file_path} - all expected functions found")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Function definition test failed: {str(e)}")
        return False


def test_decorator_usage():
    """Test that @tool decorators are used correctly"""
    logger.info("Testing @tool decorator usage...")
    
    try:
        import ast
        
        tool_files = [
            'tools/product_search_tool.py',
            'tools/cart_management_tool.py',
            'tools/order_query_tool.py',
            'tools/knowledge_base_tool.py'
        ]
        
        for file_path in tool_files:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Find functions with @tool decorator
            tool_functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for @tool decorator
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                            tool_functions.append(node.name)
                        elif isinstance(decorator, ast.Attribute) and decorator.attr == 'tool':
                            tool_functions.append(node.name)
            
            if tool_functions:
                logger.info(f"✓ {file_path} - found @tool decorated functions: {tool_functions}")
            else:
                logger.warning(f"⚠ {file_path} - no @tool decorated functions found")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Decorator usage test failed: {str(e)}")
        return False


def test_model_definitions():
    """Test that Pydantic models are properly defined"""
    logger.info("Testing Pydantic model definitions...")
    
    try:
        import ast
        
        with open('models.py', 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find class definitions
        class_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)
        
        expected_models = [
            'ProductInfo', 'ProductSearchResponse', 'ProductRecommendation',
            'CartSummary', 'CartItem', 'CartOperation',
            'OrderHistory', 'OrderInfo', 'OrderTracking',
            'AgentResponse', 'ErrorResponse', 'KnowledgeResponse'
        ]
        
        missing_models = []
        for model_name in expected_models:
            if model_name not in class_names:
                missing_models.append(model_name)
        
        if missing_models:
            logger.error(f"✗ Missing Pydantic models: {missing_models}")
            return False
        else:
            logger.info(f"✓ All expected Pydantic models found: {len(expected_models)} models")
            return True
        
    except Exception as e:
        logger.error(f"✗ Model definition test failed: {str(e)}")
        return False


def run_structure_tests():
    """Run all structure tests"""
    logger.info("=" * 60)
    logger.info("STRANDS AI AGENT TOOLS STRUCTURE TEST")
    logger.info("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Basic Imports", test_basic_imports),
        ("Tool Function Definitions", test_tool_function_definitions),
        ("Decorator Usage", test_decorator_usage),
        ("Model Definitions", test_model_definitions)
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
        logger.info("🎉 All structure tests passed! Tools are properly structured.")
        return True
    else:
        logger.warning(f"⚠ {total - passed} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = run_structure_tests()
    sys.exit(0 if success else 1)