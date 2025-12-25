#!/usr/bin/env python3
"""
Recreate the knowledge base index with proper knn_vector mapping
"""

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def recreate_knowledge_base_index():
    """Delete and recreate the knowledge base index with proper mapping"""
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
        
        # Delete existing index if it exists
        if client.indices.exists(index='knowledge-base'):
            print("🗑️  Deleting existing knowledge-base index...")
            client.indices.delete(index='knowledge-base')
            print("✅ Index deleted")
        
        # Create index with proper knn_vector mapping
        print("🔧 Creating new knowledge-base index with knn_vector mapping...")
        
        index_mapping = {
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
                    },
                    "source": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "timestamp": {"type": "date"},
                    "document_type": {"type": "keyword"},
                    "metadata": {
                        "properties": {
                            "file_extension": {"type": "keyword"},
                            "chunk_size": {"type": "integer"},
                            "created_at": {"type": "date"}
                        }
                    }
                }
            },
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            }
        }
        
        response = client.indices.create(
            index='knowledge-base',
            body=index_mapping
        )
        
        if response.get('acknowledged', False):
            print("✅ Knowledge base index created successfully with knn_vector mapping")
            
            # Verify the mapping
            mapping = client.indices.get_mapping(index='knowledge-base')
            embedding_type = mapping['knowledge-base']['mappings']['properties']['embedding']['type']
            print(f"📋 Embedding field type: {embedding_type}")
            
            if embedding_type == 'knn_vector':
                print("🎉 Index is ready for vector similarity search!")
                return True
            else:
                print("❌ Mapping verification failed")
                return False
        else:
            print("❌ Failed to create index")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Recreating Knowledge Base Index")
    print("=" * 50)
    success = recreate_knowledge_base_index()
    
    if success:
        print("\n✅ Index recreation completed successfully!")
        print("You can now upload documents to test Nova embeddings with vector search.")
    else:
        print("\n❌ Index recreation failed. Check the errors above.")