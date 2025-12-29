"""
Test script to verify Strands SDK imports in Lambda environment
"""

def handler(event, context):
    """Test handler to check imports"""
    results = {
        "imports": {},
        "errors": []
    }
    
    # Test basic imports
    try:
        import strands
        results["imports"]["strands"] = "OK"
        results["strands_version"] = getattr(strands, '__version__', 'unknown')
    except Exception as e:
        results["imports"]["strands"] = f"FAILED: {type(e).__name__}: {str(e)}"
        results["errors"].append(f"strands import: {str(e)}")
    
    # Test Agent import
    try:
        from strands import Agent
        results["imports"]["strands.Agent"] = "OK"
    except Exception as e:
        results["imports"]["strands.Agent"] = f"FAILED: {type(e).__name__}: {str(e)}"
        results["errors"].append(f"Agent import: {str(e)}")
    
    # Test BedrockModel import
    try:
        from strands.models import BedrockModel
        results["imports"]["strands.models.BedrockModel"] = "OK"
    except Exception as e:
        results["imports"]["strands.models.BedrockModel"] = f"FAILED: {type(e).__name__}: {str(e)}"
        results["errors"].append(f"BedrockModel import: {str(e)}")
    
    # Test ConversationManager import
    try:
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        results["imports"]["strands.agent.conversation_manager.SlidingWindowConversationManager"] = "OK"
    except Exception as e:
        results["imports"]["strands.agent.conversation_manager.SlidingWindowConversationManager"] = f"FAILED: {type(e).__name__}: {str(e)}"
        results["errors"].append(f"SlidingWindowConversationManager import: {str(e)}")
    
    # Test boto3
    try:
        import boto3
        results["imports"]["boto3"] = "OK"
        results["boto3_version"] = boto3.__version__
    except Exception as e:
        results["imports"]["boto3"] = f"FAILED: {type(e).__name__}: {str(e)}"
        results["errors"].append(f"boto3 import: {str(e)}")
    
    # Check environment variables
    import os
    results["environment"] = {
        "MEMORY_ID": os.environ.get('MEMORY_ID', 'NOT_SET'),
        "MODEL_ID": os.environ.get('MODEL_ID', 'NOT_SET'),
        "AWS_REGION": os.environ.get('AWS_REGION', 'NOT_SET'),
        "GUARDRAIL_ID": os.environ.get('GUARDRAIL_ID', 'NOT_SET')
    }
    
    # Check Lambda layers
    import sys
    results["python_path"] = sys.path
    
    return {
        "statusCode": 200,
        "body": results
    }
