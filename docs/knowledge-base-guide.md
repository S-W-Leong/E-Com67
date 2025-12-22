# E-Com67 Knowledge Base Implementation Guide

## Overview

The E-Com67 platform includes an advanced S3-based knowledge base that enhances the AI chat assistant with semantic search capabilities. This implementation uses Amazon Bedrock for embeddings generation and OpenSearch for vector similarity search.

## Architecture

### Components

1. **S3 Bucket**: Stores original text documents
2. **Knowledge Processor Lambda**: Processes documents and generates embeddings
3. **OpenSearch Collection**: Stores embeddings and provides vector search
4. **Enhanced Chat Function**: Uses knowledge base for contextual responses
5. **Knowledge Manager**: Utility for managing documents

### Data Flow

```
Document Upload → S3 → Lambda Trigger → Knowledge Processor
                                              ↓
                                    Generate Embeddings (Bedrock)
                                              ↓
                                    Store in OpenSearch (Vector Index)

User Query → Chat Function → Generate Query Embedding → Vector Search
                                              ↓
                                    Retrieve Similar Chunks → Enhanced Response
```

## Implementation Details

### S3 Bucket Structure

```
e-com67-knowledge-base-{account}-{region}/
├── documents/
│   ├── product-guides/
│   │   ├── laptop-buying-guide.txt
│   │   └── smartphone-features.md
│   ├── policies/
│   │   ├── shipping-policy.txt
│   │   └── return-policy.txt
│   └── support/
│       └── customer-support.txt
```

### OpenSearch Index Schema

The knowledge base uses a specialized index with vector search capabilities:

```json
{
  "mappings": {
    "properties": {
      "text": {"type": "text"},
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil"
        }
      },
      "source": {"type": "keyword"},
      "chunk_index": {"type": "integer"},
      "timestamp": {"type": "date"}
    }
  }
}
```

### Embedding Generation

- **Model**: Amazon Titan Embed Text v1
- **Dimensions**: 1536
- **Chunking**: 1000 characters with 200 character overlap
- **Similarity**: Cosine similarity for vector search

## Usage

### Managing Documents

#### Upload Sample Documents

```bash
python scripts/manage_knowledge_base.py upload-samples
```

#### Upload Individual Document

```bash
python scripts/manage_knowledge_base.py upload path/to/document.txt
```

#### Upload Directory

```bash
python scripts/manage_knowledge_base.py upload-dir path/to/documents/
```

#### List Documents

```bash
python scripts/manage_knowledge_base.py list
```

#### Delete Document

```bash
python scripts/manage_knowledge_base.py delete document.txt
```

### Using the Knowledge Base in Chat

The enhanced chat function automatically:

1. Generates embeddings for user queries
2. Searches the knowledge base for relevant context
3. Includes relevant information in AI responses

Example interaction:
```
User: "What's your shipping policy?"
AI: "Based on our shipping policy, E-Com67 offers free shipping on orders over $50. We have three shipping options: Standard (5-7 days, free over $50), Express (2-3 days, $9.99), and Overnight (1 day, $19.99)..."
```

## Configuration

### Environment Variables

**Knowledge Processor Function:**
- `KNOWLEDGE_BASE_BUCKET_NAME`: S3 bucket for documents
- `OPENSEARCH_ENDPOINT`: OpenSearch collection endpoint
- `EMBEDDING_MODEL_ID`: Bedrock embedding model ID

**Chat Function:**
- `OPENSEARCH_ENDPOINT`: OpenSearch collection endpoint
- `EMBEDDING_MODEL_ID`: Bedrock embedding model ID

### IAM Permissions

The Lambda functions require the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::knowledge-base-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": "arn:aws:aoss:*:*:collection/e-com67-products"
    }
  ]
}
```

## Supported File Types

The knowledge base supports the following text file types:
- `.txt` - Plain text files
- `.md`, `.markdown` - Markdown files
- `.rst` - reStructuredText files
- `.json` - JSON files
- `.csv` - CSV files
- `.html`, `.htm` - HTML files
- `.xml` - XML files
- `.yaml`, `.yml` - YAML files

## Performance Considerations

### Chunking Strategy

- **Chunk Size**: 1000 characters (optimal for context preservation)
- **Overlap**: 200 characters (ensures continuity across chunks)
- **Boundary Detection**: Prefers sentence boundaries over word boundaries

### Search Performance

- **Vector Dimensions**: 1536 (Amazon Titan standard)
- **Search Algorithm**: HNSW (Hierarchical Navigable Small World)
- **Similarity Metric**: Cosine similarity
- **Search Limit**: 3-5 most relevant chunks per query

### Cost Optimization

- **Embedding Generation**: ~$0.0001 per 1K tokens
- **OpenSearch Storage**: ~$0.24 per GB per month
- **S3 Storage**: ~$0.023 per GB per month
- **Lambda Execution**: Pay per invocation and duration

## Monitoring and Troubleshooting

### CloudWatch Metrics

The knowledge base generates the following custom metrics:
- `DocumentsProcessed`: Number of documents successfully processed
- `EmbeddingsGenerated`: Number of embeddings created
- `EmbeddingsStored`: Number of embeddings stored in OpenSearch
- `DocumentProcessingErrors`: Number of processing failures

### Common Issues

#### Document Processing Failures

1. **Check file format**: Ensure file is a supported text format
2. **Verify permissions**: Lambda needs S3 read permissions
3. **Check Bedrock access**: Verify model access permissions
4. **Monitor memory usage**: Large documents may need more memory

#### Search Not Working

1. **Verify OpenSearch index**: Check if knowledge-base index exists
2. **Check embeddings**: Verify documents were processed successfully
3. **Test connectivity**: Ensure Lambda can reach OpenSearch endpoint
4. **Review IAM permissions**: Verify OpenSearch access permissions

#### Poor Search Results

1. **Review document quality**: Ensure documents contain relevant information
2. **Check chunking**: Verify text is being chunked appropriately
3. **Test query phrasing**: Try different ways of asking questions
4. **Monitor similarity scores**: Check if scores are reasonable (>0.7 is good)

## Testing

### Unit Tests

Run the knowledge base tests:

```bash
python -m pytest tests/test_knowledge_base.py -v
```

### Integration Testing

1. Upload sample documents
2. Verify processing in CloudWatch logs
3. Test chat queries with knowledge base content
4. Check OpenSearch index for stored embeddings

### Manual Testing

```python
# Test document upload
python scripts/manage_knowledge_base.py upload-samples

# Test chat with knowledge base
# Use WebSocket client or frontend to ask questions like:
# "What's your return policy?"
# "How do I track my order?"
# "What products do you sell?"
```

## Future Enhancements

### Planned Improvements

1. **Multi-modal Support**: Support for PDF, Word documents
2. **Advanced Chunking**: Semantic chunking based on content structure
3. **Metadata Filtering**: Filter search results by document type or date
4. **Relevance Tuning**: Machine learning-based relevance scoring
5. **Real-time Updates**: Immediate index updates for document changes

### Scaling Considerations

1. **Distributed Processing**: Use SQS for batch document processing
2. **Caching Layer**: Add Redis for frequently accessed embeddings
3. **Multi-region**: Replicate knowledge base across regions
4. **Auto-scaling**: Dynamic scaling based on query volume

## Security

### Data Protection

- **Encryption at Rest**: S3 and OpenSearch use AWS managed encryption
- **Encryption in Transit**: All API calls use HTTPS/TLS
- **Access Control**: IAM policies restrict access to authorized functions
- **Audit Logging**: CloudTrail logs all API access

### Best Practices

1. **Principle of Least Privilege**: Grant minimal required permissions
2. **Regular Updates**: Keep dependencies and models updated
3. **Content Validation**: Sanitize uploaded documents
4. **Access Monitoring**: Monitor unusual access patterns
5. **Backup Strategy**: Regular backups of critical documents

## Conclusion

The S3-based knowledge base significantly enhances the E-Com67 AI assistant by providing semantic search capabilities over a curated set of documents. This implementation demonstrates modern AI/ML patterns using AWS managed services while maintaining cost efficiency and scalability.

The system provides a solid foundation for building more advanced knowledge management features and can be extended to support various content types and use cases.