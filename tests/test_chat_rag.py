#!/usr/bin/env python3
"""
WebSocket Chat RAG Testing Script

Tests the knowledge base RAG functionality through the actual chat WebSocket interface.
"""

import asyncio
import websockets
import json
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatRAGTester:
    def __init__(self, websocket_url, auth_token=None):
        self.websocket_url = websocket_url
        self.auth_token = auth_token
        self.session_id = f"test-session-{int(time.time())}"
        
    async def test_knowledge_base_queries(self):
        """Test knowledge base queries through WebSocket chat"""
        
        # Test queries that should trigger knowledge base
        test_queries = [
            {
                'query': 'What is your shipping policy?',
                'expected_topics': ['shipping', 'delivery', 'free shipping', 'cost'],
                'should_use_kb': True
            },
            {
                'query': 'How do I return an item?',
                'expected_topics': ['return', 'refund', 'policy', 'days'],
                'should_use_kb': True
            },
            {
                'query': 'What payment methods do you accept?',
                'expected_topics': ['payment', 'credit card', 'paypal', 'methods'],
                'should_use_kb': True
            },
            {
                'query': 'Can you help me find a laptop?',
                'expected_topics': ['laptop', 'product', 'search'],
                'should_use_kb': False  # Should use product search tool instead
            },
            {
                'query': 'Tell me about your company history',
                'expected_topics': ['company', 'history', 'about'],
                'should_use_kb': True
            }
        ]
        
        results = []
        
        try:
            # Build WebSocket URL with auth
            ws_url = self.websocket_url
            if self.auth_token:
                ws_url += f"?token={self.auth_token}&sessionId={self.session_id}"
            else:
                ws_url += f"?sessionId={self.session_id}"
            
            async with websockets.connect(ws_url) as websocket:
                logger.info(f"Connected to WebSocket: {self.websocket_url}")
                
                # Wait for welcome message
                welcome_msg = await websocket.recv()
                logger.info(f"Received welcome: {json.loads(welcome_msg)}")
                
                for test_case in test_queries:
                    logger.info(f"Testing query: '{test_case['query']}'")
                    
                    # Send message
                    message = {
                        'action': 'sendMessage',
                        'message': test_case['query'],
                        'sessionId': self.session_id,
                        'timestamp': int(time.time() * 1000)
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Wait for response (with timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)
                        
                        # Analyze response
                        result = self.analyze_response(test_case, response_data)
                        results.append(result)
                        
                        # Log result
                        status = "✓" if result['success'] else "✗"
                        logger.info(f"{status} Query result - KB used: {result['kb_used']}, Relevant: {result['relevant']}")
                        
                        # Wait between queries
                        await asyncio.sleep(2)
                        
                    except asyncio.TimeoutError:
                        logger.error(f"✗ Timeout waiting for response to: {test_case['query']}")
                        results.append({
                            'query': test_case['query'],
                            'success': False,
                            'error': 'timeout',
                            'kb_used': False,
                            'relevant': False
                        })
                
        except Exception as e:
            logger.error(f"WebSocket test failed: {str(e)}")
            return None
        
        return results
    
    def analyze_response(self, test_case, response_data):
        """Analyze chat response for knowledge base usage and relevance"""
        
        query = test_case['query']
        expected_topics = test_case['expected_topics']
        should_use_kb = test_case['should_use_kb']
        
        # Extract response content
        message_content = response_data.get('message', '').lower()
        response_data_field = response_data.get('data', {})
        tools_used = response_data_field.get('tools_used', [])
        
        # Check if knowledge base tool was used
        kb_used = any('knowledge' in tool.lower() for tool in tools_used)
        
        # Check relevance by looking for expected topics
        relevant = any(topic.lower() in message_content for topic in expected_topics)
        
        # Check response quality indicators
        has_specific_info = len(message_content) > 50  # Substantial response
        has_structured_data = bool(response_data_field.get('data'))
        
        # Determine success
        success = True
        
        if should_use_kb and not kb_used:
            success = False
            logger.warning(f"Expected knowledge base usage for: {query}")
        
        if not relevant:
            success = False
            logger.warning(f"Response not relevant to query: {query}")
        
        if not has_specific_info:
            success = False
            logger.warning(f"Response too generic for: {query}")
        
        return {
            'query': query,
            'success': success,
            'kb_used': kb_used,
            'relevant': relevant,
            'tools_used': tools_used,
            'response_length': len(message_content),
            'has_structured_data': has_structured_data,
            'response_preview': message_content[:100] + "..." if len(message_content) > 100 else message_content
        }


async def main():
    """Run WebSocket chat RAG tests"""
    logger.info("=" * 80)
    logger.info("WEBSOCKET CHAT RAG TESTING")
    logger.info("=" * 80)
    
    # Configuration - update these with your actual values
    WEBSOCKET_URL = "wss://your-websocket-id.execute-api.ap-southeast-1.amazonaws.com/prod"
    AUTH_TOKEN = None  # Add your auth token if needed
    
    # Check if URL is configured
    if "your-websocket-id" in WEBSOCKET_URL:
        logger.error("Please update WEBSOCKET_URL with your actual WebSocket endpoint")
        logger.info("You can find it by running:")
        logger.info("aws cloudformation describe-stacks --stack-name E-Com67-ApiStack --query \"Stacks[0].Outputs[?OutputKey=='WebSocketApiUrl'].OutputValue\" --output text")
        return False
    
    tester = ChatRAGTester(WEBSOCKET_URL, AUTH_TOKEN)
    
    try:
        results = await tester.test_knowledge_base_queries()
        
        if results is None:
            logger.error("WebSocket testing failed")
            return False
        
        # Analyze results
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS")
        logger.info("=" * 80)
        
        successful_tests = [r for r in results if r['success']]
        kb_usage_tests = [r for r in results if r['kb_used']]
        
        logger.info(f"Total queries tested: {len(results)}")
        logger.info(f"Successful responses: {len(successful_tests)}")
        logger.info(f"Knowledge base used: {len(kb_usage_tests)}")
        
        # Detailed results
        for result in results:
            status = "✓" if result['success'] else "✗"
            kb_status = "KB" if result['kb_used'] else "No KB"
            logger.info(f"{status} {result['query'][:40]:<40} | {kb_status} | Tools: {result['tools_used']}")
        
        # Success criteria
        success_rate = len(successful_tests) / len(results)
        kb_usage_rate = len(kb_usage_tests) / len(results)
        
        logger.info(f"\nSuccess rate: {success_rate:.1%}")
        logger.info(f"Knowledge base usage rate: {kb_usage_rate:.1%}")
        
        if success_rate >= 0.8:
            logger.info("🎉 WebSocket chat RAG testing passed!")
            return True
        else:
            logger.warning("⚠ WebSocket chat RAG testing needs improvement")
            return False
            
    except Exception as e:
        logger.error(f"Testing failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)