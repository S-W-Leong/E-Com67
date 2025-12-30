"""
Knowledge Base Tool for Strands AI Agent - Enhanced RAG Integration

This tool enables the Strands agent to search and retrieve information from
the E-Com67 platform's knowledge base for answering questions about policies,
shipping, returns, and general platform information. Enhanced with improved
multi-source synthesis, freshness indication, and fallback mechanisms.
"""

# CRITICAL: Apply OpenTelemetry fix BEFORE any other imports
import otel_fix  # Stubs out OpenTelemetry - we use Powertools for tracing

import json
import os
import logging
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from strands import tool
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import KnowledgeResponse, KnowledgeSource

# Initialize logger
logger = logging.getLogger(__name__)

# Environment variables
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
EMBEDDING_MODEL_ID = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')
EMBEDDING_REGION = os.environ.get('EMBEDDING_REGION', 'us-east-1')  # Cross-region inference
KNOWLEDGE_INDEX = 'knowledge-base'

# Knowledge base configuration
KNOWLEDGE_FRESHNESS_THRESHOLD_DAYS = 30  # Consider content stale after 30 days
MAX_SOURCES_FOR_SYNTHESIS = 5  # Maximum sources to use for answer synthesis
FALLBACK_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence for fallback responses
EMBEDDING_DIMENSION = 1024  # Nova Multimodal Embeddings dimension

# Initialize AWS services
bedrock_runtime = None
opensearch_client = None


def get_bedrock_runtime():
    """Get Bedrock Runtime client with lazy initialization for cross-region inference"""
    global bedrock_runtime
    if bedrock_runtime is None:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=EMBEDDING_REGION)
    return bedrock_runtime


def get_opensearch_client():
    """Get OpenSearch client with lazy initialization"""
    global opensearch_client
    if opensearch_client is None:
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from requests_aws4auth import AWS4Auth
            
            # Set up AWS authentication for OpenSearch
            host = OPENSEARCH_ENDPOINT.replace('https://', '')
            region = AWS_REGION
            service = 'es'  # For regular OpenSearch Service
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                service,
                session_token=credentials.token
            )
            
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
    return opensearch_client


class KnowledgeBaseTool:
    """Enhanced knowledge base search tool for Strands agent with RAG integration using Nova embeddings"""
    
    def __init__(self):
        """Initialize the knowledge base tool"""
        self.freshness_threshold = timedelta(days=KNOWLEDGE_FRESHNESS_THRESHOLD_DAYS)
        self.current_time = datetime.utcnow()
    
    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for search query using Amazon Nova Multimodal Embeddings"""
        try:
            bedrock_client = get_bedrock_runtime()
            if not bedrock_client:
                logger.error("Bedrock runtime client not available")
                return None
            
            # Prepare request for Bedrock (Nova format)
            request_body = {
                "taskType": "SINGLE_EMBEDDING",
                "singleEmbeddingParams": {
                    "embeddingPurpose": "GENERIC_QUERY",  # For query processing
                    "embeddingDimension": EMBEDDING_DIMENSION,
                    "text": {
                        "truncationMode": "END",  # Truncate from end if text is too long
                        "value": query[:8000]  # Nova has text length limits
                    }
                }
            }
            
            # Call Bedrock with cross-region inference
            response = bedrock_client.invoke_model(
                modelId=EMBEDDING_MODEL_ID,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response (Nova format)
            response_body = json.loads(response['body'].read())
            embeddings = response_body.get('embeddings', [])
            
            if not embeddings or len(embeddings) == 0:
                logger.error("No embeddings returned from Nova model")
                return None
                
            embedding = embeddings[0]['embedding']  # Get first (and only) embedding
            
            if len(embedding) != EMBEDDING_DIMENSION:
                logger.error(f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSION}")
                return None
            
            logger.debug(f"Generated query embedding with dimension {len(embedding)} using Nova model in {EMBEDDING_REGION}")
            
            return embedding
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Bedrock error generating query embedding ({error_code}): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            return None
    
    def format_knowledge_source(self, source_data: Dict[str, Any], relevance_score: float = 0.0) -> KnowledgeSource:
        """
        Format knowledge source data into KnowledgeSource model.
        
        Args:
            source_data: Raw knowledge source data
            relevance_score: Relevance score for the source
            
        Returns:
            KnowledgeSource model instance
        """
        # Handle timestamp conversion
        last_updated = source_data.get('lastUpdated', time.time())
        if isinstance(last_updated, (int, float)):
            last_updated_dt = datetime.fromtimestamp(last_updated)
        elif isinstance(last_updated, str):
            try:
                last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            except ValueError:
                last_updated_dt = datetime.utcnow()
        else:
            last_updated_dt = last_updated if isinstance(last_updated, datetime) else datetime.utcnow()
        
        return KnowledgeSource(
            source_id=source_data.get('sourceId', ''),
            title=source_data.get('title', 'Untitled'),
            content=source_data.get('content', ''),
            category=source_data.get('category', 'general'),
            last_updated=last_updated_dt,
            relevance_score=relevance_score,
            url=source_data.get('url')
        )
    
    def is_content_fresh(self, source: KnowledgeSource) -> bool:
        """
        Check if knowledge source content is considered fresh.
        
        Args:
            source: Knowledge source to check
            
        Returns:
            True if content is fresh, False if stale
        """
        age = self.current_time - source.last_updated
        return age <= self.freshness_threshold
    
    def categorize_sources_by_freshness(self, sources: List[KnowledgeSource]) -> Dict[str, List[KnowledgeSource]]:
        """
        Categorize sources by freshness for better synthesis.
        
        Args:
            sources: List of knowledge sources
            
        Returns:
            Dictionary with 'fresh' and 'stale' source lists
        """
        fresh_sources = []
        stale_sources = []
        
        for source in sources:
            if self.is_content_fresh(source):
                fresh_sources.append(source)
            else:
                stale_sources.append(source)
        
        return {
            'fresh': fresh_sources,
            'stale': stale_sources
        }
    
    def synthesize_answer(self, sources: List[KnowledgeSource], query: str) -> str:
        """
        Enhanced answer synthesis from multiple knowledge sources with freshness indication.
        
        Args:
            sources: List of relevant knowledge sources
            query: Original user query
            
        Returns:
            Synthesized answer text with freshness indicators
        """
        if not sources:
            return self._generate_no_knowledge_response(query)
        
        # Categorize sources by freshness
        categorized = self.categorize_sources_by_freshness(sources)
        fresh_sources = categorized['fresh']
        stale_sources = categorized['stale']
        
        # Sort sources by relevance within each category
        fresh_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        stale_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Prioritize fresh sources for synthesis
        primary_sources = fresh_sources[:MAX_SOURCES_FOR_SYNTHESIS]
        if len(primary_sources) < MAX_SOURCES_FOR_SYNTHESIS:
            # Add stale sources if needed, but with lower priority
            remaining_slots = MAX_SOURCES_FOR_SYNTHESIS - len(primary_sources)
            primary_sources.extend(stale_sources[:remaining_slots])
        
        if not primary_sources:
            return self._generate_no_knowledge_response(query)
        
        # Build synthesized answer
        answer_parts = []
        
        # Start with the most relevant source
        primary_source = primary_sources[0]
        answer_parts.append(primary_source.content)
        
        # Add complementary information from other sources
        used_categories = {primary_source.category}
        for source in primary_sources[1:]:
            # Add information from different categories or highly relevant same-category sources
            if (source.category not in used_categories and source.relevance_score > 0.5) or \
               (source.category == primary_source.category and source.relevance_score > 0.7):
                
                # Format additional information appropriately
                if source.category != primary_source.category:
                    answer_parts.append(f"Additionally, regarding {source.category}: {source.content}")
                else:
                    answer_parts.append(f"Also, {source.content}")
                
                used_categories.add(source.category)
        
        # Combine answer parts
        synthesized_answer = " ".join(answer_parts)
        
        # Add freshness and source attribution
        attribution_parts = []
        
        if fresh_sources:
            attribution_parts.append(f"Based on {len(fresh_sources)} current source{'s' if len(fresh_sources) > 1 else ''}")
        
        if stale_sources and any(s in primary_sources for s in stale_sources):
            stale_count = len([s for s in primary_sources if s in stale_sources])
            if stale_count > 0:
                attribution_parts.append(f"{stale_count} source{'s' if stale_count > 1 else ''} may be outdated")
        
        if attribution_parts:
            synthesized_answer += f"\n\n({', '.join(attribution_parts)} from our knowledge base.)"
        
        # Add freshness warning if using primarily stale sources
        if len(stale_sources) > len(fresh_sources) and stale_sources:
            oldest_source = min(stale_sources, key=lambda x: x.last_updated)
            days_old = (self.current_time - oldest_source.last_updated).days
            synthesized_answer += f"\n\nNote: Some information may be outdated (last updated {days_old} days ago). For the most current information, please contact customer support."
        
        return synthesized_answer
    
    def _generate_no_knowledge_response(self, query: str) -> str:
        """
        Generate appropriate response when no knowledge is found.
        
        Args:
            query: Original user query
            
        Returns:
            Helpful response with alternative suggestions
        """
        # Analyze query to provide more specific guidance
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['shipping', 'delivery', 'ship']):
            return ("I don't have specific information about shipping in my current knowledge base. "
                   "For detailed shipping information, please check your account dashboard or contact "
                   "customer support at support@e-com67.com.")
        
        elif any(word in query_lower for word in ['return', 'refund', 'exchange']):
            return ("I don't have current return policy information available. "
                   "For return and refund questions, please visit our returns page or contact "
                   "customer support for assistance.")
        
        elif any(word in query_lower for word in ['payment', 'billing', 'charge']):
            return ("For payment and billing questions, please check your account settings or "
                   "contact customer support. They can help with payment methods, billing issues, "
                   "and transaction details.")
        
        elif any(word in query_lower for word in ['account', 'login', 'password']):
            return ("For account-related questions, please visit your account dashboard or "
                   "contact customer support. They can help with login issues, account settings, "
                   "and security questions.")
        
        else:
            return ("I don't have specific information about that topic in my current knowledge base. "
                   "Please contact customer support at support@e-com67.com or use our live chat "
                   "for personalized assistance.")
    
    def calculate_confidence(self, sources: List[KnowledgeSource], query: str) -> float:
        """
        Enhanced confidence calculation considering source freshness and relevance.
        
        Args:
            sources: List of knowledge sources used
            query: Original user query
            
        Returns:
            Confidence score between 0 and 1
        """
        if not sources:
            return 0.0
        
        # Base confidence on relevance scores
        relevance_scores = [source.relevance_score for source in sources]
        max_relevance = max(relevance_scores)
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        # Start with combined relevance score
        confidence = (max_relevance * 0.7) + (avg_relevance * 0.3)
        
        # Boost confidence for multiple agreeing sources
        if len(sources) > 1:
            confidence += 0.1
        
        # Adjust confidence based on source freshness
        categorized = self.categorize_sources_by_freshness(sources)
        fresh_count = len(categorized['fresh'])
        stale_count = len(categorized['stale'])
        
        if fresh_count > stale_count:
            # Boost confidence for fresh sources
            confidence += 0.15
        elif stale_count > fresh_count:
            # Reduce confidence for primarily stale sources
            confidence -= 0.1
        
        # Boost confidence for high-relevance fresh sources
        high_relevance_fresh = [s for s in categorized['fresh'] if s.relevance_score > 0.8]
        if high_relevance_fresh:
            confidence += 0.1
        
        # Ensure confidence stays within bounds
        return max(0.0, min(confidence, 1.0))


@tool
def search_knowledge_base(query: str, category: Optional[str] = None, limit: int = 5) -> KnowledgeResponse:
    """
    Search the E-Com67 knowledge base for information about policies, shipping, returns, and platform features.
    Enhanced with multi-source synthesis, freshness indication, and improved fallback mechanisms.
    
    Args:
        query: Search query (e.g., "return policy", "shipping times", "payment methods")
        category: Optional category filter (e.g., "shipping", "returns", "policies", "account")
        limit: Maximum number of sources to retrieve (default: 5, max: 10)
        
    Returns:
        KnowledgeResponse with relevant information, synthesized answer, and freshness indicators
    """
    logger.info(f"Enhanced knowledge base search: query='{query}', category={category}, limit={limit}")
    
    start_time = time.time()
    
    # Validate and sanitize inputs
    limit = max(1, min(limit, 10))  # Ensure reasonable limits
    query = query.strip()
    
    if not query:
        return KnowledgeResponse(
            query=query,
            sources=[],
            synthesized_answer="Please provide a specific question for me to search our knowledge base.",
            confidence=0.0,
            search_time_ms=int((time.time() - start_time) * 1000)
        )
    
    try:
        # Initialize enhanced knowledge base tool
        kb_tool = KnowledgeBaseTool()
        
        # Check if OpenSearch is configured
        if not OPENSEARCH_ENDPOINT:
            logger.warning("OpenSearch endpoint not configured, using fallback")
            sources = kb_tool.get_fallback_knowledge(query, category)
        else:
            try:
                # Use Nova embeddings with OpenSearch vector search
                sources = kb_tool._search_opensearch_knowledge_base(query, category, limit)
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.error(f"Nova embedding generation failed ({error_code}): {str(e)}")
                
                # Use fallback with appropriate confidence adjustment
                sources = kb_tool.get_fallback_knowledge(query, category)
                
            except Exception as e:
                logger.error(f"Knowledge base search failed: {str(e)}")
                # Use fallback for any other errors
                sources = kb_tool.get_fallback_knowledge(query, category)
        
        # Enhanced answer synthesis with freshness indication
        synthesized_answer = kb_tool.synthesize_answer(sources, query)
        
        # Enhanced confidence calculation
        confidence = kb_tool.calculate_confidence(sources, query)
        
        # Calculate search time
        search_time_ms = int((time.time() - start_time) * 1000)
        
        knowledge_response = KnowledgeResponse(
            query=query,
            sources=sources,
            synthesized_answer=synthesized_answer,
            confidence=confidence,
            search_time_ms=search_time_ms
        )
        
        logger.info(f"Enhanced knowledge base search completed: {len(sources)} sources, confidence {confidence:.2f}, fresh sources: {len([s for s in sources if kb_tool.is_content_fresh(s)])}")
        
        return knowledge_response
        
    except Exception as e:
        logger.error(f"Unexpected error in enhanced knowledge base search: {str(e)}")
        
        # Return enhanced error response with helpful suggestions
        return KnowledgeResponse(
            query=query,
            sources=[],
            synthesized_answer=kb_tool._generate_no_knowledge_response(query) if 'kb_tool' in locals() else 
                             "I'm having trouble accessing the knowledge base right now. Please try again later or contact customer support for assistance.",
            confidence=0.0,
            search_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _search_opensearch_knowledge_base(self, query: str, category: Optional[str], limit: int) -> List[KnowledgeSource]:
        """
        Search OpenSearch knowledge base using Nova embeddings for vector similarity search.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results to return
            
        Returns:
            List of knowledge sources from OpenSearch
        """
        opensearch_client = get_opensearch_client()
        if not opensearch_client:
            logger.error("OpenSearch client not available")
            raise Exception("OpenSearch client not available")
        
        # Generate embedding for the query using Nova
        query_embedding = self.generate_query_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            raise Exception("Failed to generate query embedding")
        
        # Build OpenSearch query with vector similarity search
        search_body = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": limit * 2  # Get more candidates for better filtering
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["text", "source", "chunk_index", "timestamp", "metadata"]
        }
        
        # Add category filter if specified
        if category:
            # Try to match category in source path or metadata
            search_body["query"]["bool"]["filter"] = [
                {
                    "bool": {
                        "should": [
                            {"wildcard": {"source": f"*{category}*"}},
                            {"term": {"metadata.category": category}}
                        ]
                    }
                }
            ]
        
        try:
            # Execute search with timeout handling
            response = opensearch_client.search(
                index=KNOWLEDGE_INDEX,
                body=search_body,
                timeout='10s'
            )
        except Exception as e:
            logger.error(f"OpenSearch query failed: {str(e)}")
            raise e
        
        # Process search results
        sources = []
        search_hits = response.get('hits', {}).get('hits', [])
        
        for hit in search_hits:
            try:
                source_data = hit.get('_source', {})
                score = hit.get('_score', 0.0)
                
                # Skip empty or very short content
                content = source_data.get('text', '').strip()
                if len(content) < 10:
                    continue
                
                # Normalize score to 0-1 range (OpenSearch scores can vary widely)
                # Typical cosine similarity scores are between 0.5-1.0 for relevant content
                normalized_score = min(max((score - 0.5) * 2, 0.0), 1.0)
                
                # Create knowledge source with enhanced metadata handling
                metadata = source_data.get('metadata', {})
                timestamp = source_data.get('timestamp', time.time())
                
                formatted_source_data = {
                    'sourceId': f"os_{hit.get('_id', len(sources))}",
                    'title': self._extract_title_from_source(source_data.get('source', '')),
                    'content': content,
                    'category': self._extract_category_from_source(source_data.get('source', ''), category),
                    'lastUpdated': timestamp,
                    'url': None  # OpenSearch doesn't store URLs in our current setup
                }
                
                knowledge_source = self.format_knowledge_source(formatted_source_data, normalized_score)
                sources.append(knowledge_source)
                
            except Exception as e:
                logger.warning(f"Error processing search result: {str(e)}")
                continue
        
        logger.info(f"OpenSearch returned {len(sources)} relevant sources for query: {query}")
        return sources
    
    def _extract_title_from_source(self, source_path: str) -> str:
        """Extract a readable title from the source file path"""
        if not source_path:
            return "Knowledge Base Article"
        
        # Get filename without extension
        filename = source_path.split('/')[-1]
        if '.' in filename:
            filename = '.'.join(filename.split('.')[:-1])
        
        # Convert underscores/hyphens to spaces and title case
        title = filename.replace('_', ' ').replace('-', ' ').title()
        
        return title if title else "Knowledge Base Article"
    
    def _extract_category_from_source(self, source_path: str, provided_category: Optional[str]) -> str:
        """Extract category from source path or use provided category"""
        if provided_category:
            return provided_category
        
        # Try to extract category from path
        path_lower = source_path.lower()
        
        # Common category keywords
        if any(word in path_lower for word in ['ship', 'deliver']):
            return 'shipping'
        elif any(word in path_lower for word in ['return', 'refund']):
            return 'returns'
        elif any(word in path_lower for word in ['payment', 'billing']):
            return 'payment'
        elif any(word in path_lower for word in ['account', 'profile']):
            return 'account'
        elif any(word in path_lower for word in ['policy', 'terms']):
            return 'policies'
        else:
            return 'general'
    
    def get_fallback_knowledge(self, query: str, category: Optional[str] = None) -> List[KnowledgeSource]:
        """
        Enhanced fallback knowledge with better categorization and freshness simulation.
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List of fallback knowledge sources with realistic timestamps
        """
        logger.info("Using enhanced fallback knowledge base")
        
        # Enhanced fallback knowledge base with more realistic timestamps
        current_time = time.time()
        fallback_knowledge = {
            'shipping': [
                {
                    'sourceId': 'shipping_001',
                    'title': 'Standard Shipping Information',
                    'content': 'Standard shipping takes 3-5 business days and costs $5.99. Free shipping is available on orders over $50. We ship Monday through Friday, excluding holidays.',
                    'category': 'shipping',
                    'lastUpdated': current_time - 86400 * 2,  # 2 days ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'shipping_002',
                    'title': 'Express Shipping Options',
                    'content': 'Express shipping (1-2 business days) is available for $12.99. Same-day delivery is available in select cities for $19.99. Express orders must be placed before 2 PM.',
                    'category': 'shipping',
                    'lastUpdated': current_time - 86400 * 5,  # 5 days ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'shipping_003',
                    'title': 'International Shipping',
                    'content': 'International shipping is available to most countries. Delivery times vary by destination (7-21 business days). Additional customs fees may apply.',
                    'category': 'shipping',
                    'lastUpdated': current_time - 86400 * 45,  # 45 days ago (stale)
                    'url': None
                }
            ],
            'returns': [
                {
                    'sourceId': 'returns_001',
                    'title': 'Return Policy Overview',
                    'content': 'Items can be returned within 30 days of purchase for a full refund. Items must be in original condition with tags attached. Original packaging is preferred but not required.',
                    'category': 'returns',
                    'lastUpdated': current_time - 86400 * 7,  # 1 week ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'returns_002',
                    'title': 'Return Process Steps',
                    'content': 'To return an item: 1) Go to your order history, 2) Click "Return Item", 3) Select reason for return, 4) Print the prepaid return label, 5) Drop off at any shipping location.',
                    'category': 'returns',
                    'lastUpdated': current_time - 86400 * 10,  # 10 days ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'returns_003',
                    'title': 'Refund Processing Times',
                    'content': 'Refunds are processed within 3-5 business days after we receive your returned item. The refund will appear on your original payment method.',
                    'category': 'returns',
                    'lastUpdated': current_time - 86400 * 14,  # 2 weeks ago (fresh)
                    'url': None
                }
            ],
            'payment': [
                {
                    'sourceId': 'payment_001',
                    'title': 'Accepted Payment Methods',
                    'content': 'We accept all major credit cards (Visa, MasterCard, American Express, Discover), PayPal, Apple Pay, and Google Pay. Payment is processed securely at checkout using industry-standard encryption.',
                    'category': 'payment',
                    'lastUpdated': current_time - 86400 * 3,  # 3 days ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'payment_002',
                    'title': 'Payment Security',
                    'content': 'All payment information is encrypted and processed through secure payment gateways. We never store your complete credit card information on our servers.',
                    'category': 'payment',
                    'lastUpdated': current_time - 86400 * 20,  # 20 days ago (fresh)
                    'url': None
                }
            ],
            'account': [
                {
                    'sourceId': 'account_001',
                    'title': 'Account Management',
                    'content': 'You can update your account information, view order history, manage payment methods, and update shipping addresses in your account dashboard. Access your account by clicking "My Account" in the top menu.',
                    'category': 'account',
                    'lastUpdated': current_time - 86400 * 5,  # 5 days ago (fresh)
                    'url': None
                },
                {
                    'sourceId': 'account_002',
                    'title': 'Password Reset',
                    'content': 'To reset your password, click "Forgot Password" on the login page. Enter your email address and we\'ll send you a secure reset link. The link expires after 24 hours.',
                    'category': 'account',
                    'lastUpdated': current_time - 86400 * 8,  # 8 days ago (fresh)
                    'url': None
                }
            ],
            'policies': [
                {
                    'sourceId': 'policies_001',
                    'title': 'Privacy Policy Summary',
                    'content': 'We protect your personal information and only use it to process orders and improve your shopping experience. We never sell your data to third parties.',
                    'category': 'policies',
                    'lastUpdated': current_time - 86400 * 60,  # 60 days ago (stale)
                    'url': None
                },
                {
                    'sourceId': 'policies_002',
                    'title': 'Terms of Service',
                    'content': 'By using our platform, you agree to our terms of service. This includes our return policy, shipping terms, and user conduct guidelines.',
                    'category': 'policies',
                    'lastUpdated': current_time - 86400 * 90,  # 90 days ago (stale)
                    'url': None
                }
            ]
        }
        
        # Enhanced search logic with better relevance scoring
        query_lower = query.lower()
        relevant_sources = []
        
        # If category is specified, search only in that category
        if category and category in fallback_knowledge:
            search_categories = [category]
        else:
            search_categories = fallback_knowledge.keys()
        
        for cat in search_categories:
            for source_data in fallback_knowledge.get(cat, []):
                # Enhanced relevance scoring
                content_lower = source_data['content'].lower()
                title_lower = source_data['title'].lower()
                
                score = 0.0
                query_words = query_lower.split()
                
                # Score based on exact phrase matches (higher weight)
                if query_lower in content_lower:
                    score += 0.5
                if query_lower in title_lower:
                    score += 0.6
                
                # Score based on individual word matches
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        if word in title_lower:
                            score += 0.3
                        if word in content_lower:
                            score += 0.2
                        if word in cat:
                            score += 0.15
                
                # Boost score for category match
                if category and cat == category:
                    score += 0.2
                
                # Only include sources with meaningful relevance
                if score > FALLBACK_CONFIDENCE_THRESHOLD:
                    knowledge_source = self.format_knowledge_source(source_data, score)
                    relevant_sources.append(knowledge_source)
        
        # Sort by relevance and return top results
        relevant_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant_sources[:5]


@tool
def get_platform_info(topic: str) -> str:
    """
    Get comprehensive information about the E-Com67 platform features and capabilities.
    Enhanced with more detailed information and freshness indicators.
    
    Args:
        topic: Information topic (e.g., "features", "security", "support", "about", "mobile", "privacy")
        
    Returns:
        Detailed information about the requested topic with freshness indication
    """
    logger.info(f"Platform info requested: topic='{topic}'")
    
    topic_lower = topic.lower()
    
    # Enhanced platform information with more comprehensive details
    platform_info = {
        'features': {
            'content': "E-Com67 is a modern e-commerce platform offering: intelligent product search with AI-powered recommendations, advanced shopping cart management with real-time inventory updates, secure checkout with multiple payment options, comprehensive order tracking with real-time updates, AI-powered customer support available 24/7, personalized product recommendations based on browsing history, mobile-responsive design for seamless shopping across all devices, and advanced security features including two-factor authentication.",
            'last_updated': 'Current (updated regularly)'
        },
        
        'security': {
            'content': "E-Com67 implements enterprise-grade security measures: SSL/TLS encryption for all data transmission, PCI DSS compliance for payment processing, secure tokenization of payment information (we never store complete card details), regular security audits and penetration testing, two-factor authentication for account protection, automated fraud detection systems, secure API endpoints with rate limiting, and 24/7 security monitoring. All personal data is encrypted at rest and in transit.",
            'last_updated': 'Current (security measures updated monthly)'
        },
        
        'support': {
            'content': "Customer support is available through multiple channels: AI-powered chat assistant available 24/7 for instant help, human support team available Monday-Friday 9 AM - 6 PM EST, email support with response within 24 hours, comprehensive help center with detailed guides, video tutorials for common tasks, community forum for user discussions, and priority support for premium customers. Our AI assistant can help with orders, products, shipping, returns, and account management.",
            'last_updated': 'Current (support options updated weekly)'
        },
        
        'about': {
            'content': "E-Com67 is a next-generation e-commerce platform built with modern cloud technologies on AWS. Founded with a mission to provide exceptional customer experience, we focus on intelligent product discovery, personalized recommendations, fast and reliable service, and innovative AI-powered features. Our platform serves thousands of customers worldwide with a 99.9% uptime guarantee and industry-leading performance.",
            'last_updated': 'Current (company information updated quarterly)'
        },
        
        'mobile': {
            'content': "E-Com67 is fully optimized for mobile devices with: responsive web design that adapts to any screen size, progressive web app (PWA) capabilities for app-like experience, touch-optimized interface for easy navigation, mobile-specific features like one-tap checkout, camera integration for barcode scanning, push notifications for order updates, offline browsing capabilities, and fast loading times optimized for mobile networks. No app download required - access everything through your mobile browser.",
            'last_updated': 'Current (mobile features updated monthly)'
        },
        
        'account': {
            'content': "Your E-Com67 account provides: secure login with optional two-factor authentication, complete order history with detailed tracking, saved payment methods with secure tokenization, multiple shipping addresses management, personalized product recommendations based on your preferences, wishlist and favorites functionality, email preferences and notification settings, account security settings and activity monitoring, and easy account recovery options. Creating an account is free and enhances your shopping experience.",
            'last_updated': 'Current (account features updated regularly)'
        },
        
        'privacy': {
            'content': "E-Com67 is committed to protecting your privacy: we collect only information necessary to provide our services, your data is never sold to third parties, we use industry-standard encryption for data protection, you have full control over your personal information, we comply with GDPR and other privacy regulations, we provide transparent privacy policies in plain language, you can request data deletion at any time, and we conduct regular privacy audits. See our complete privacy policy for detailed information on data handling practices.",
            'last_updated': 'Current (privacy policy updated quarterly)'
        },
        
        'shipping': {
            'content': "E-Com67 offers flexible shipping options: standard shipping (3-5 business days) for $5.99, free shipping on orders over $50, express shipping (1-2 business days) for $12.99, same-day delivery in select cities for $19.99, international shipping to most countries, real-time tracking for all shipments, packaging with eco-friendly materials, and shipping insurance available for valuable items.",
            'last_updated': 'Current (shipping information updated weekly)'
        },
        
        'returns': {
            'content': "E-Com67 has a customer-friendly return policy: 30-day return window for most items, free return shipping with prepaid labels, full refund to original payment method, easy return process through your account, no restocking fees for standard returns, extended return periods during holidays, and dedicated return support team to assist with any issues.",
            'last_updated': 'Current (return policy updated monthly)'
        }
    }
    
    # Find matching information with enhanced search
    best_match = None
    best_score = 0
    
    for key, info in platform_info.items():
        score = 0
        if key in topic_lower or topic_lower in key:
            score = 1.0  # Exact match
        else:
            # Partial matching for related terms
            topic_words = topic_lower.split()
            for word in topic_words:
                if word in key or word in info['content'].lower():
                    score += 0.3
        
        if score > best_score:
            best_score = score
            best_match = info
    
    if best_match and best_score > 0.3:
        return f"{best_match['content']}\n\nInformation Status: {best_match['last_updated']}"
    
    # Enhanced default response for unknown topics
    return f"I don't have specific information about '{topic}' in my current knowledge base. However, I can help you with information about our platform features, security measures, customer support, account management, mobile experience, privacy policies, shipping options, or return procedures. Please contact customer support at support@e-com67.com for detailed information about specific topics not covered in my knowledge base."


@tool
def get_help_topics() -> List[str]:
    """
    Get a comprehensive list of available help topics and categories.
    Enhanced with more detailed categorization.
    
    Returns:
        List of available help topic categories with descriptions
    """
    logger.info("Enhanced help topics requested")
    
    help_topics = [
        "Shipping & Delivery - Information about shipping options, delivery times, and tracking",
        "Returns & Refunds - Return policy, refund process, and exchange procedures", 
        "Payment Methods - Accepted payment options, billing, and payment security",
        "Account Management - Creating accounts, login issues, and profile settings",
        "Order Tracking - How to track orders, delivery updates, and order history",
        "Product Information - Product details, availability, and specifications",
        "Platform Features - Website functionality, mobile app, and new features",
        "Security & Privacy - Data protection, account security, and privacy policies",
        "Customer Support - How to contact support and available support channels",
        "Technical Issues - Website problems, browser compatibility, and troubleshooting",
        "International Orders - Global shipping, customs, and international policies",
        "Business Accounts - Bulk orders, business pricing, and corporate features"
    ]
    
    return help_topics


@tool
def search_help_by_category(category: str, specific_topic: Optional[str] = None) -> KnowledgeResponse:
    """
    Search for help information within a specific category.
    Enhanced tool for more targeted knowledge retrieval.
    
    Args:
        category: Help category (e.g., "shipping", "returns", "payment", "account")
        specific_topic: Optional specific topic within the category
        
    Returns:
        KnowledgeResponse with category-specific information
    """
    logger.info(f"Category-specific help search: category='{category}', topic='{specific_topic}'")
    
    # Build search query
    if specific_topic:
        query = f"{category} {specific_topic}"
    else:
        query = category
    
    # Use the main search function with category filter
    return search_knowledge_base(query=query, category=category.lower(), limit=3)