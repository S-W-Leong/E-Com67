#!/usr/bin/env python3
"""
Debug script to test Strands imports in the Lambda environment.
"""

import sys
import os

# Simulate Lambda environment
sys.path.insert(0, '/opt/python')

def test_imports():
    """Test imports step by step to identify the exact issue."""
    
    print("=== Strands Import Debug ===")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path[:3]}")
    
    # Test basic Python imports first
    try:
        import json
        import boto3
        print("✓ Basic Python imports work")
    except Exception as e:
        print(f"✗ Basic Python imports failed: {e}")
        return
    
    # Test if we can import from the layer
    try:
        # Add layer path
        layer_path = '/opt/python'
        if layer_path not in sys.path:
            sys.path.insert(0, layer_path)
        
        # Try importing strands
        import strands
        print(f"✓ Strands import successful from: {strands.__file__}")
        
        # Test specific imports
        from strands import Agent
        print("✓ Agent import successful")
        
        from strands.models import BedrockModel
        print("✓ BedrockModel import successful")
        
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        print("✓ SlidingWindowConversationManager import successful")
        
        print("✓ All Strands imports successful!")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print(f"  Error type: {type(e)}")
        
        # Try to get more details about the missing module
        if hasattr(e, 'name'):
            print(f"  Missing module: {e.name}")
        
        # Check what's actually available
        try:
            import strands
            print(f"  Strands module location: {strands.__file__}")
            print(f"  Strands module contents: {dir(strands)}")
        except:
            print("  Cannot import strands at all")
            
        return False
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        print(f"  Error type: {type(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_imports()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")