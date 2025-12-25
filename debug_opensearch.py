#!/usr/bin/env python3
"""
Debug script to check OpenSearch document structure
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def debug_opensearch():
    """Debug OpenSearch documents"""
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
        
        # Get index mapping
        print("📋 Index mapping:")
        mapping = client.indices.get_mapping(index='knowledge-base')
        print(json.dumps(mapping, indent=2))
        
        print("\n" + "="*50)
        
        # Get all documents with full source
        search_body = {
            "query": {"match_all": {}},
            "size": 10
        }
        
        response = client.search(index='knowledge-base', body=search_body)
        
        print(f"📄 Found {response['hits']['total']['value']} documents:")
        for i, hit in enumerate(response['hits']['hits']):
            print(f"\n--- Document {i+1} ---")
            print(f"ID: {hit['_id']}")
            source = hit['_source']
            
            # Print all fields
            for key, value in source.items():
                if key == 'embedding':
                    if value:
                        print(f"{key}: [array of {len(value)} floats] - First 3: {value[:3]}")
                    else:
                        print(f"{key}: None or empty")
                elif key == 'text':
                    text_preview = value[:100] + "..." if len(value) > 100 else value
                    print(f"{key}: {text_preview}")
                else:
                    print(f"{key}: {value}")
        
        return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Debugging OpenSearch Documents")
    print("=" * 50)
    debug_opensearch()