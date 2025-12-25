#!/usr/bin/env python3
"""
RAG Quality and Performance Testing

Tests the quality and performance of the knowledge base RAG system.
"""

import time
import statistics
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGQualityTester:
    def __init__(self):
        self.test_cases = [
            {
                'query': 'What is your shipping policy?',
                'expected_keywords': ['shipping', 'delivery', 'free', 'cost', 'business days'],
                'quality_threshold': 0.7,
                'response_time_threshold': 5.0  # seconds
            },
            {
                'query': 'How do I return an item?',
                'expected_keywords': ['return', 'refund', 'policy', 'days', 'condition'],
                'quality_threshold': 0.7,
                'response_time_threshold': 5.0
            },
            {
                'query': 'What payment methods do you accept?',
                'expected_keywords': ['payment', 'credit', 'card', 'paypal', 'methods'],
                'quality_threshold': 0.6,
                'response_time_threshold': 5.0
            }
        ]
    
    def test_response_quality(self, query: str, response: str, expected_keywords: List[str]) -> Dict[str, Any]:
        """Test the quality of a RAG response"""
        
        response_lower = response.lower()
        
        # Keyword coverage
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response_lower]
        keyword_coverage = len(found_keywords) / len(expected_keywords)
        
        # Response length (should be substantial)
        length_score = min(len(response) / 200, 1.0)  # Normalize to 200 chars
        
        # Specificity (avoid generic responses)
        generic_phrases = ['i can help', 'let me assist', 'please contact', 'i understand']
        generic_count = sum(1 for phrase in generic_phrases if phrase in response_lower)
        specificity_score = max(0, 1 - (generic_count * 0.2))
        
        # Overall quality score
        quality_score = (keyword_coverage * 0.5) + (length_score * 0.3) + (specificity_score * 0.2)
        
        return {
            'keyword_coverage': keyword_coverage,
            'found_keywords': found_keywords,
            'length_score': length_score,
            'specificity_score': specificity_score,
            'quality_score': quality_score,
            'response_length': len(response)
        }
    
    def test_response_time(self, query_func, query: str, iterations: int = 3) -> Dict[str, Any]:
        """Test response time performance"""
        
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = query_func(query)
                end_time = time.time()
                response_time = end_time - start_time
                times.append(response_time)
                
                logger.info(f"Iteration {i+1}: {response_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Query failed on iteration {i+1}: {str(e)}")
                times.append(float('inf'))
        
        # Filter out failed attempts
        valid_times = [t for t in times if t != float('inf')]
        
        if not valid_times:
            return {
                'success': False,
                'error': 'All iterations failed'
            }
        
        return {
            'success': True,
            'avg_time': statistics.mean(valid_times),
            'min_time': min(valid_times),
            'max_time': max(valid_times),
            'std_dev': statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            'success_rate': len(valid_times) / iterations
        }
    
    def test_consistency(self, query_func, query: str, iterations: int = 3) -> Dict[str, Any]:
        """Test response consistency across multiple calls"""
        
        responses = []
        
        for i in range(iterations):
            try:
                response = query_func(query)
                responses.append(response)
                logger.info(f"Response {i+1} length: {len(response)} chars")
                
            except Exception as e:
                logger.error(f"Query failed on iteration {i+1}: {str(e)}")
                responses.append("")
        
        # Analyze consistency
        valid_responses = [r for r in responses if r]
        
        if len(valid_responses) < 2:
            return {
                'success': False,
                'error': 'Not enough valid responses for consistency analysis'
            }
        
        # Check length consistency
        lengths = [len(r) for r in valid_responses]
        length_consistency = 1 - (statistics.stdev(lengths) / statistics.mean(lengths))
        
        # Check keyword consistency (simplified)
        all_words = set()
        for response in valid_responses:
            words = set(response.lower().split())
            all_words.update(words)
        
        common_words = set(valid_responses[0].lower().split())
        for response in valid_responses[1:]:
            common_words &= set(response.lower().split())
        
        keyword_consistency = len(common_words) / len(all_words) if all_words else 0
        
        overall_consistency = (length_consistency * 0.6) + (keyword_consistency * 0.4)
        
        return {
            'success': True,
            'length_consistency': length_consistency,
            'keyword_consistency': keyword_consistency,
            'overall_consistency': overall_consistency,
            'response_count': len(valid_responses)
        }


def mock_rag_query(query: str) -> str:
    """Mock RAG query function for testing"""
    # This would be replaced with actual RAG system call
    time.sleep(1.5)  # Simulate processing time
    
    # Mock responses based on query
    if 'shipping' in query.lower():
        return "E-Com67 offers free shipping on orders over $50. Standard shipping takes 3-5 business days and costs $5.99. Express shipping (2-3 days) costs $9.99, and overnight shipping costs $19.99. We ship to most countries worldwide."
    
    elif 'return' in query.lower():
        return "Items can be returned within 30 days of purchase for a full refund. Items must be in original condition with tags attached. Return shipping is free for defective items, otherwise customer pays return shipping costs."
    
    elif 'payment' in query.lower():
        return "We accept all major credit cards (Visa, MasterCard, American Express), PayPal, Apple Pay, and Google Pay. All payments are processed securely through our encrypted payment system."
    
    else:
        return "I can help you with information about our products and services. Please let me know what specific information you're looking for."


def main():
    """Run RAG quality and performance tests"""
    logger.info("=" * 80)
    logger.info("RAG QUALITY AND PERFORMANCE TESTING")
    logger.info("=" * 80)
    
    tester = RAGQualityTester()
    
    overall_results = {
        'quality_tests': [],
        'performance_tests': [],
        'consistency_tests': []
    }
    
    for test_case in tester.test_cases:
        query = test_case['query']
        expected_keywords = test_case['expected_keywords']
        quality_threshold = test_case['quality_threshold']
        time_threshold = test_case['response_time_threshold']
        
        logger.info(f"\n--- Testing: {query} ---")
        
        # Test response quality
        logger.info("Testing response quality...")
        try:
            response = mock_rag_query(query)
            quality_result = tester.test_response_quality(query, response, expected_keywords)
            quality_result['query'] = query
            quality_result['meets_threshold'] = quality_result['quality_score'] >= quality_threshold
            overall_results['quality_tests'].append(quality_result)
            
            logger.info(f"Quality score: {quality_result['quality_score']:.2f} (threshold: {quality_threshold})")
            logger.info(f"Keywords found: {quality_result['found_keywords']}")
            
        except Exception as e:
            logger.error(f"Quality test failed: {str(e)}")
        
        # Test performance
        logger.info("Testing response time...")
        try:
            perf_result = tester.test_response_time(mock_rag_query, query)
            perf_result['query'] = query
            perf_result['meets_threshold'] = perf_result.get('avg_time', float('inf')) <= time_threshold
            overall_results['performance_tests'].append(perf_result)
            
            if perf_result['success']:
                logger.info(f"Avg response time: {perf_result['avg_time']:.2f}s (threshold: {time_threshold}s)")
            
        except Exception as e:
            logger.error(f"Performance test failed: {str(e)}")
        
        # Test consistency
        logger.info("Testing response consistency...")
        try:
            consistency_result = tester.test_consistency(mock_rag_query, query)
            consistency_result['query'] = query
            overall_results['consistency_tests'].append(consistency_result)
            
            if consistency_result['success']:
                logger.info(f"Consistency score: {consistency_result['overall_consistency']:.2f}")
            
        except Exception as e:
            logger.error(f"Consistency test failed: {str(e)}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    # Quality summary
    quality_tests = overall_results['quality_tests']
    quality_passed = sum(1 for t in quality_tests if t.get('meets_threshold', False))
    logger.info(f"Quality tests: {quality_passed}/{len(quality_tests)} passed")
    
    # Performance summary
    perf_tests = overall_results['performance_tests']
    perf_passed = sum(1 for t in perf_tests if t.get('meets_threshold', False))
    logger.info(f"Performance tests: {perf_passed}/{len(perf_tests)} passed")
    
    # Consistency summary
    consistency_tests = overall_results['consistency_tests']
    consistency_passed = sum(1 for t in consistency_tests if t.get('success', False))
    logger.info(f"Consistency tests: {consistency_passed}/{len(consistency_tests)} passed")
    
    total_passed = quality_passed + perf_passed + consistency_passed
    total_tests = len(quality_tests) + len(perf_tests) + len(consistency_tests)
    
    logger.info(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        logger.info("🎉 All RAG quality and performance tests passed!")
    else:
        logger.warning("⚠ Some tests failed. Review the results above.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)