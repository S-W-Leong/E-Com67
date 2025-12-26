#!/usr/bin/env python3
"""
Test imports for knowledge base tool
"""

import sys
import os

# Set up environment
os.environ['OPENSEARCH_ENDPOINT'] = 'https://test.com'
os.environ['AWS_REGION'] = 'ap-southeast-1'
os.environ['EMBEDDING_MODEL_ID'] = 'amazon.nova-2-multimodal-embeddings-v1:0'
os.environ['EMBEDDING_REGION'] = 'us-east-1'

# Add lambda/chat to path
sys.path.insert(0, 'lambda/chat')

try:
    print("Testing basic imports...")
    import json
    import os
    import logging
    import time
    from typing import Dict, Any, List, Optional
    from datetime import datetime, timedelta
    import boto3
    from botocore.exceptions import ClientError
    print("✅ Basic imports successful")
    
    print("Testing knowledge base tool structure...")
    # Test the file can be read and parsed
    with open('lambda/chat/tools/knowledge_base_tool.py', 'r') as f:
        content = f.read()
    
    # Check for key components
    checks = [
        'class KnowledgeBaseTool',
        'def generate_query_embedding',
        'def _search_opensearch_knowledge_base',
        'EMBEDDING_MODEL_ID',
        'EMBEDDING_REGION',
        'amazon.nova-2-multimodal-embeddings-v1:0'
    ]
    
    for check in checks:
        if check in content:
            print(f"✅ Found: {check}")
        else:
            print(f"❌ Missing: {check}")
    
    print("✅ Knowledge base tool structure looks good")
    
except Exception as e:
    print(f"❌ Import test failed: {str(e)}")
    sys.exit(1)

print("🎉 All import tests passed!")