#!/usr/bin/env python3
"""
Test RAG search functionality with Nova embeddings
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def generate_query_embedding(query_text):
    """Generate embedding for search query using Nova"""
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        request_body = {
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": "GENERIC_INDEX",  # Use same purpose as documents for consistency
                "embeddingDimension": 1024,
                "text": {
                    "truncationMode": "END",
                    "value": query_text
                }
            }
        }
        
        response = bedrock.invoke_model(
            modelId="amazon.nova-2-multimodal-embeddings-v1:0",
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        embeddings = response_body.get('embeddings', [])
        
        if embeddings and len(embeddings) > 0:
            return embeddings[0]['embedding']
        return None
        
    except Exception as e:
        print(f"❌ Error generating query embedding: {str(e)}")
        return None

def search_knowledge_base(query_text, top_k=3):
    """Search knowledge base using vector similarity"""
    try:
        # Generate query embedding
        print(f"🔍 Searching for: '{query_text}'")
        query_embedding = generate_query_embedding(query_text)
        
        if not query_embedding:
            print("❌ Failed to generate query embedding")
            return []
        
        print(f"✅ Generated query embedding ({len(query_embedding)} dimensions)")
        
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
        
        # Perform vector similarity search
        search_body = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k
                    }
                }
            },
            "_source": ["text", "source", "chunk_index"],
            "size": top_k
        }
        
        response = client.search(index='knowledge-base', body=search_body)
        
        results = []
        print(f"\n📊 Found {len(response['hits']['hits'])} results:")
        
        for i, hit in enumerate(response['hits']['hits']):
            score = hit['_score']
            source = hit['_source']
            
            result = {
                'score': score,
                'text': source['text'],
                'source': source['source'],
                'chunk_index': source['chunk_index']
            }
            results.append(result)
            
            print(f"\n--- Result {i+1} (Score: {score:.4f}) ---")
            print(f"Source: {source['source']} (chunk {source['chunk_index']})")
            text_preview = source['text'][:200] + "..." if len(source['text']) > 200 else source['text']
            print(f"Text: {text_preview}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error searching knowledge base: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_rag_queries():
    """Test various RAG queries"""
    test_queries = [
        "What is E-Com67?",
        "How does the AI chat system work?",
        "What AWS services are used?",
        "Tell me about the architecture",
        "What features does the platform have?"
    ]
    
    print("🧪 Testing RAG Search with Nova Embeddings")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        results = search_knowledge_base(query, top_k=2)
        
        if results:
            print(f"✅ Search successful for: '{query}'")
        else:
            print(f"❌ No results for: '{query}'")
        
        print("-" * 40)

if __name__ == "__main__":
    test_rag_queries()