"""
E-Com67 Platform Knowledge Processor Function

Processes documents uploaded to S3, generates embeddings using Amazon Bedrock,
and stores them in OpenSearch for vector similarity search.
"""

import json
import boto3
import os
import time
import uuid
import re
from typing import List, Dict, Any, Optional
from urllib.parse import unquote_plus
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients (will be initialized lazily)
s3_client = None
bedrock_runtime = None
opensearch_client = None

# Environment variables
KNOWLEDGE_BASE_BUCKET = os.environ.get('KNOWLEDGE_BASE_BUCKET_NAME')
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
EMBEDDING_MODEL_ID = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
KNOWLEDGE_INDEX = 'knowledge-base'

# Constants
MAX_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_DIMENSION = 1536  # Amazon Titan embedding dimension


def _initialize_aws_clients():
    """Initialize AWS clients lazily to avoid issues during testing"""
    global s3_client, bedrock_runtime, opensearch_client
    
    if s3_client is None:
        s3_client = boto3.client('s3')
    
    if bedrock_runtime is None:
        bedrock_runtime = boto3.client('bedrock-runtime')
    
    if opensearch_client is None:
        # Import opensearch client from layer
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from aws_requests_auth.aws_auth import AWSRequestsAuth
            
            # Set up AWS authentication for OpenSearch
            host = OPENSEARCH_ENDPOINT.replace('https://', '')
            region = os.environ.get('AWS_REGION', 'ap-southeast-1')
            service = 'es'  # Changed from 'aoss' to 'es' for regular OpenSearch Service
            credentials = boto3.Session().get_credentials()
            awsauth = AWSRequestsAuth(credentials, region, service)
            
            opensearch_client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
        except ImportError as e:
            logger.error(f"Failed to import OpenSearch client: {str(e)}")
            opensearch_client = None


class KnowledgeProcessorError(Exception):
    """Custom exception for knowledge processor errors"""
    pass


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main handler for S3 document processing events.
    
    Processes documents uploaded to S3 and creates embeddings for knowledge base.
    """
    try:
        # Initialize AWS clients
        _initialize_aws_clients()
        
        if opensearch_client is None:
            raise KnowledgeProcessorError("OpenSearch client not available")
        
        processed_documents = 0
        
        # Process each S3 event record
        for record in event.get('Records', []):
            if record['eventName'].startswith('ObjectCreated'):
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                logger.info(f"Processing document: s3://{bucket}/{key}")
                
                # Process the document
                success = process_document(bucket, key)
                if success:
                    processed_documents += 1
                    metrics.add_metric(name="DocumentsProcessed", unit=MetricUnit.Count, value=1)
                else:
                    metrics.add_metric(name="DocumentProcessingErrors", unit=MetricUnit.Count, value=1)
            
            elif record['eventName'].startswith('ObjectRemoved'):
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                logger.info(f"Removing document from knowledge base: s3://{bucket}/{key}")
                
                # Remove document from knowledge base
                success = remove_document_from_knowledge_base(key)
                if success:
                    metrics.add_metric(name="DocumentsRemoved", unit=MetricUnit.Count, value=1)
                else:
                    metrics.add_metric(name="DocumentRemovalErrors", unit=MetricUnit.Count, value=1)
        
        logger.info(f"Successfully processed {processed_documents} documents")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {processed_documents} documents',
                'processedDocuments': processed_documents
            })
        }
        
    except Exception as e:
        logger.exception(f"Error processing knowledge base documents: {str(e)}")
        metrics.add_metric(name="ProcessingErrors", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process knowledge base documents',
                'message': str(e)
            })
        }


def process_document(bucket: str, key: str) -> bool:
    """Process a single document and create embeddings"""
    try:
        # Skip non-text files
        if not is_text_file(key):
            logger.info(f"Skipping non-text file: {key}")
            return True
        
        # Download document from S3
        logger.debug(f"Downloading document from S3: {key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8', errors='ignore')
        
        if not content.strip():
            logger.warning(f"Document is empty: {key}")
            return True
        
        # Clean and preprocess content
        content = clean_text(content)
        
        # Split into chunks
        chunks = split_text_into_chunks(content, MAX_CHUNK_SIZE, CHUNK_OVERLAP)
        logger.info(f"Split document {key} into {len(chunks)} chunks")
        
        # Process each chunk
        successful_chunks = 0
        for i, chunk in enumerate(chunks):
            if process_chunk(key, i, chunk):
                successful_chunks += 1
        
        logger.info(f"Successfully processed {successful_chunks}/{len(chunks)} chunks for document {key}")
        
        return successful_chunks > 0
        
    except Exception as e:
        logger.exception(f"Error processing document {key}: {str(e)}")
        return False


def process_chunk(document_key: str, chunk_index: int, chunk_text: str) -> bool:
    """Process a single text chunk and store in knowledge base"""
    try:
        # Generate embedding for the chunk
        embedding = generate_embedding(chunk_text)
        if not embedding:
            logger.error(f"Failed to generate embedding for chunk {chunk_index} of {document_key}")
            return False
        
        # Create document ID
        document_id = f"{document_key.replace('/', '_')}_{chunk_index}"
        
        # Store in OpenSearch
        return store_embedding(document_id, chunk_text, embedding, document_key, chunk_index)
        
    except Exception as e:
        logger.exception(f"Error processing chunk {chunk_index} of {document_key}: {str(e)}")
        return False


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Amazon Bedrock Titan"""
    try:
        # Prepare request for Bedrock
        request_body = {
            "inputText": text
        }
        
        # Call Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding', [])
        
        if len(embedding) != EMBEDDING_DIMENSION:
            logger.error(f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSION}")
            return None
        
        logger.debug(f"Generated embedding with dimension {len(embedding)}")
        metrics.add_metric(name="EmbeddingsGenerated", unit=MetricUnit.Count, value=1)
        
        return embedding
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.exception(f"Bedrock error ({error_code}): {str(e)}")
        metrics.add_metric(name="BedrockErrors", unit=MetricUnit.Count, value=1)
        return None
    except Exception as e:
        logger.exception(f"Error generating embedding: {str(e)}")
        return None


def store_embedding(doc_id: str, text: str, embedding: List[float], source: str, chunk_index: int) -> bool:
    """Store embedding in OpenSearch knowledge base index"""
    try:
        # Prepare document for indexing
        document = {
            'text': text,
            'embedding': embedding,
            'source': source,
            'chunk_index': chunk_index,
            'timestamp': int(time.time()),
            'document_type': 'knowledge_base',
            'metadata': {
                'file_extension': source.split('.')[-1] if '.' in source else 'txt',
                'chunk_size': len(text),
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        }
        
        # Index document in OpenSearch
        response = opensearch_client.index(
            index=KNOWLEDGE_INDEX,
            id=doc_id,
            body=document,
            refresh=True  # Make immediately searchable
        )
        
        if response.get('result') in ['created', 'updated']:
            logger.debug(f"Successfully stored embedding for document {doc_id}")
            metrics.add_metric(name="EmbeddingsStored", unit=MetricUnit.Count, value=1)
            return True
        else:
            logger.error(f"Unexpected OpenSearch response: {response}")
            return False
        
    except Exception as e:
        logger.exception(f"Error storing embedding for document {doc_id}: {str(e)}")
        metrics.add_metric(name="StorageErrors", unit=MetricUnit.Count, value=1)
        return False


def remove_document_from_knowledge_base(document_key: str) -> bool:
    """Remove all chunks of a document from the knowledge base"""
    try:
        # Search for all chunks of this document
        search_body = {
            "query": {
                "term": {
                    "source": document_key
                }
            },
            "_source": False,
            "size": 1000  # Assume max 1000 chunks per document
        }
        
        response = opensearch_client.search(
            index=KNOWLEDGE_INDEX,
            body=search_body
        )
        
        # Delete all found chunks
        chunks_to_delete = [hit['_id'] for hit in response['hits']['hits']]
        
        if chunks_to_delete:
            # Bulk delete
            delete_body = []
            for chunk_id in chunks_to_delete:
                delete_body.append({"delete": {"_index": KNOWLEDGE_INDEX, "_id": chunk_id}})
            
            if delete_body:
                bulk_response = opensearch_client.bulk(body=delete_body, refresh=True)
                
                # Check for errors
                if bulk_response.get('errors'):
                    logger.error(f"Errors during bulk delete: {bulk_response}")
                    return False
                
                logger.info(f"Removed {len(chunks_to_delete)} chunks for document {document_key}")
                return True
        else:
            logger.info(f"No chunks found for document {document_key}")
            return True
        
    except Exception as e:
        logger.exception(f"Error removing document {document_key} from knowledge base: {str(e)}")
        return False


def split_text_into_chunks(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for better context preservation"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of this chunk
        end = start + max_chunk_size
        
        # If we're not at the end of the text, try to break at a sentence or word boundary
        if end < len(text):
            # Look for sentence boundary (. ! ?)
            sentence_end = text.rfind('.', start, end)
            if sentence_end == -1:
                sentence_end = text.rfind('!', start, end)
            if sentence_end == -1:
                sentence_end = text.rfind('?', start, end)
            
            if sentence_end > start + max_chunk_size // 2:  # Don't make chunks too small
                end = sentence_end + 1
            else:
                # Look for word boundary
                word_end = text.rfind(' ', start, end)
                if word_end > start + max_chunk_size // 2:
                    end = word_end
        
        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = max(start + max_chunk_size - overlap, end)
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks


def clean_text(text: str) -> str:
    """Clean and preprocess text content"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text.strip()


def is_text_file(key: str) -> bool:
    """Check if the file is a text file that should be processed"""
    text_extensions = {
        '.txt', '.md', '.markdown', '.rst', '.json', '.csv',
        '.html', '.htm', '.xml', '.yaml', '.yml'
    }
    
    # Get file extension
    extension = '.' + key.split('.')[-1].lower() if '.' in key else ''
    
    return extension in text_extensions


def ensure_knowledge_base_index() -> bool:
    """Ensure the knowledge base index exists with proper mapping"""
    try:
        # Check if index exists
        if opensearch_client.indices.exists(index=KNOWLEDGE_INDEX):
            logger.debug(f"Knowledge base index {KNOWLEDGE_INDEX} already exists")
            return True
        
        # Create index with vector mapping
        index_mapping = {
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMENSION,
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
        
        # Create the index
        response = opensearch_client.indices.create(
            index=KNOWLEDGE_INDEX,
            body=index_mapping
        )
        
        logger.info(f"Created knowledge base index: {KNOWLEDGE_INDEX}")
        return response.get('acknowledged', False)
        
    except Exception as e:
        logger.exception(f"Error creating knowledge base index: {str(e)}")
        return False


# Initialize index on module load (for warm starts)
def _initialize_index():
    """Initialize the knowledge base index if clients are available"""
    try:
        if opensearch_client is not None:
            ensure_knowledge_base_index()
    except Exception as e:
        logger.debug(f"Could not initialize index on module load: {str(e)}")


# Call initialization
_initialize_index()