#!/usr/bin/env python3
"""
Test script for Nova embeddings integration in knowledge base tool
"""

import os
import sys
import json
import boto3
from unittest.mock import patch, MagicMock

# Add lambda/chat to path for imports
sys.path.insert(0, 'lambda/chat')

# Set up test environment variables
os.environ['OPENSEARCH_ENDPOINT'] = 'https://test-opensearch.ap-southeast-1.es.amazonaws.com'
os.environ['AWS_REGION'] = 'ap-southeast-1'
os.environ['EMBEDDING_MODEL_ID'] = 'amazon.nova-2-multimodal-embeddings-v1:0'
os.environ['EMBEDDING_REGION'] = 'us-east-1'

def test_nova_embedding_generation():
    """Test Nova embedding generation"""
    print("Testing Nova embedding generation...")
    
    try:
        from tools.knowledge_base_tool import KnowledgeBaseTool
        
        # Create tool instance
        kb_tool = KnowledgeBaseTool()
        
        # Mock Bedrock response for Nova embeddings
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'embeddings': [{
                'embedding': [0.1] * 1024  # Mock 1024-dimensional embedding
            }]
        }).encode('utf-8')
        
        # Mock Bedrock client
        with patch('boto3.client') as mock_boto3:
            mock_bedrock = MagicMock()
            mock_bedrock.invoke_model.return_value = mock_response
            mock_boto3.return_value = mock_bedrock
            
            # Test embedding generation
            embedding = kb_tool.generate_query_embedding("test query")
            
            print(f"✅ Embedding generated successfully: dimension={len(embedding) if embedding else 'None'}")
            
            # Verify the call was made correctly
            mock_bedrock.invoke_model.assert_called_once()
            call_args = mock_bedrock.invoke_model.call_args
            
            # Check model ID
            assert call_args[1]['modelId'] == 'amazon.nova-2-multimodal-embeddings-v1:0'
            
            # Check request body structure
            request_body = json.loads(call_args[1]['body'])
            assert request_body['taskType'] == 'SINGLE_EMBEDDING'
            assert request_body['singleEmbeddingParams']['embeddingPurpose'] == 'GENERIC_QUERY'
            assert request_body['singleEmbeddingParams']['embeddingDimension'] == 1024
            assert request_body['singleEmbeddingParams']['text']['value'] == 'test query'
            
            print("✅ Nova API call structure is correct")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing Nova embedding generation: {str(e)}")
        return False

def test_opensearch_query_structure():
    """Test OpenSearch query structure for vector search"""
    print("\nTesting OpenSearch query structure...")
    
    try:
        from tools.knowledge_base_tool import KnowledgeBaseTool
        
        kb_tool = KnowledgeBaseTool()
        
        # Mock embedding generation
        with patch.object(kb_tool, 'generate_query_embedding') as mock_embedding:
            mock_embedding.return_value = [0.1] * 1024
            
            # Mock OpenSearch client
            mock_opensearch = MagicMock()
            mock_search_response = {
                'hits': {
                    'hits': [
                        {
                            '_id': 'test_doc_1',
                            '_score': 0.85,
                            '_source': {
                                'text': 'Test document content about shipping policies',
                                'source': 'policies/shipping.md',
                                'chunk_index': 0,
                                'timestamp': 1640995200,
                                'metadata': {'category': 'shipping'}
                            }
                        }
                    ]
                }
            }
            mock_opensearch.search.return_value = mock_search_response
            
            with patch('tools.knowledge_base_tool.get_opensearch_client') as mock_get_client:
                mock_get_client.return_value = mock_opensearch
                
                # Test search
                sources = kb_tool._search_opensearch_knowledge_base("shipping policy", None, 5)
                
                print(f"✅ Search returned {len(sources)} sources")
                
                # Verify OpenSearch query structure
                mock_opensearch.search.assert_called_once()
                call_args = mock_opensearch.search.call_args
                
                search_body = call_args[1]['body']
                
                # Check query structure
                assert 'query' in search_body
                assert 'bool' in search_body['query']
                assert 'must' in search_body['query']['bool']
                assert 'knn' in search_body['query']['bool']['must'][0]
                assert 'embedding' in search_body['query']['bool']['must'][0]['knn']
                
                # Check vector and parameters
                knn_query = search_body['query']['bool']['must'][0]['knn']['embedding']
                assert 'vector' in knn_query
                assert len(knn_query['vector']) == 1024
                assert 'k' in knn_query
                
                print("✅ OpenSearch query structure is correct")
                
                # Check source processing
                if sources:
                    source = sources[0]
                    print(f"✅ Source processed: title='{source.title}', category='{source.category}', score={source.relevance_score}")
                
                return True
                
    except Exception as e:
        print(f"❌ Error testing OpenSearch query: {str(e)}")
        return False

def test_fallback_knowledge():
    """Test fallback knowledge when OpenSearch is not available"""
    print("\nTesting fallback knowledge...")
    
    try:
        from tools.knowledge_base_tool import KnowledgeBaseTool
        
        kb_tool = KnowledgeBaseTool()
        
        # Test fallback with shipping query
        sources = kb_tool.get_fallback_knowledge("shipping times", "shipping")
        
        print(f"✅ Fallback returned {len(sources)} sources")
        
        if sources:
            for i, source in enumerate(sources[:2]):
                print(f"  Source {i+1}: {source.title} (score: {source.relevance_score:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing fallback knowledge: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Nova Embeddings Knowledge Base Integration\n")
    
    tests = [
        test_nova_embedding_generation,
        test_opensearch_query_structure,
        test_fallback_knowledge
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Nova embeddings integration looks good.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)