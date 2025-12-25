#!/usr/bin/env python3
"""
Test script to verify Nova embeddings are working correctly
"""

import boto3
import json
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def test_opensearch_connection():
    """Test connection to OpenSearch and check for knowledge base documents"""
    try:
        # Set up OpenSearch client
        opensearch_endpoint = "https://search-e-com67-products-rjgfoxl4pok4barpbwmnjxhaiq.ap-southeast-1.es.amazonaws.com"
        host = opensearch_endpoint.replace('https://', '')
        region = 'ap-southeast-1'
        service = 'es'
        
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            service,
            session_token=credentials.token
        )
        
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        
        # Check if knowledge-base index exists
        if client.indices.exists(index='knowledge-base'):
            print("✅ Knowledge base index exists")
            
            # Get index stats
            stats = client.indices.stats(index='knowledge-base')
            doc_count = stats['indices']['knowledge-base']['total']['docs']['count']
            print(f"📊 Document count: {doc_count}")
            
            # Search for documents
            search_body = {
                "query": {"match_all": {}},
                "size": 5,
                "_source": ["source", "chunk_index", "text", "timestamp"]
            }
            
            response = client.search(index='knowledge-base', body=search_body)
            
            print(f"🔍 Found {response['hits']['total']['value']} documents:")
            for hit in response['hits']['hits']:
                source = hit['_source']
                text_preview = source['text'][:100] + "..." if len(source['text']) > 100 else source['text']
                print(f"  - {source['source']} (chunk {source['chunk_index']}): {text_preview}")
                
                # Check if embedding exists and get its dimension
                if 'embedding' in source:
                    embedding_dim = len(source['embedding'])
                    print(f"    📏 Embedding dimension: {embedding_dim}")
                else:
                    print("    ❌ No embedding found")
            
            return True
        else:
            print("❌ Knowledge base index does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to OpenSearch: {str(e)}")
        return False

def test_nova_embeddings():
    """Test Nova embeddings directly"""
    try:
        # Initialize Bedrock client for us-east-1
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Test text
        test_text = "This is a test document for Nova embeddings"
        
        # Prepare request
        request_body = {
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": "GENERIC_INDEX",
                "embeddingDimension": 1024,
                "text": {
                    "truncationMode": "END",
                    "value": test_text
                }
            }
        }
        
        # Call Nova embeddings
        response = bedrock.invoke_model(
            modelId="amazon.nova-2-multimodal-embeddings-v1:0",
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        embeddings = response_body.get('embeddings', [])
        
        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]['embedding']
            print(f"✅ Nova embeddings working! Generated {len(embedding)}-dimensional embedding")
            print(f"📊 First 5 values: {embedding[:5]}")
            return True
        else:
            print("❌ No embeddings returned from Nova")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Nova embeddings: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Nova Embeddings Integration")
    print("=" * 50)
    
    print("\n1. Testing direct Nova embeddings...")
    nova_success = test_nova_embeddings()
    
    print("\n2. Testing OpenSearch connection...")
    opensearch_success = test_opensearch_connection()
    
    print("\n" + "=" * 50)
    if nova_success and opensearch_success:
        print("🎉 All tests passed! Nova embeddings are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")