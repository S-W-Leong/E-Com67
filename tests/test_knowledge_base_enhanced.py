#!/usr/bin/env python3
"""
Simple test script for enhanced knowledge base tool functionality.

This script tests the enhanced knowledge base tool without requiring
external dependencies like Pydantic or Strands SDK.
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock environment variables for testing
os.environ.setdefault('KNOWLEDGE_BASE_ID', '')  # Empty to test fallback
os.environ.setdefault('AWS_REGION', 'ap-southeast-1')

def test_knowledge_base_tool_basic():
    """Test basic knowledge base tool functionality"""
    logger.info("Testing enhanced knowledge base tool...")
    
    try:
        # Import the tool module
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Mock the models and strands imports
        class MockKnowledgeSource:
            def __init__(self, source_id, title, content, category, last_updated, relevance_score, url=None):
                self.source_id = source_id
                self.title = title
                self.content = content
                self.category = category
                self.last_updated = last_updated if isinstance(last_updated, datetime) else datetime.fromtimestamp(last_updated)
                self.relevance_score = relevance_score
                self.url = url
        
        class MockKnowledgeResponse:
            def __init__(self, query, sources, synthesized_answer, confidence, search_time_ms):
                self.query = query
                self.sources = sources
                self.synthesized_answer = synthesized_answer
                self.confidence = confidence
                self.search_time_ms = search_time_ms
        
        # Mock the imports
        sys.modules['strands'] = type('MockStrands', (), {'tool': lambda f: f})()
        sys.modules['lambda.chat.models'] = type('MockModels', (), {
            'KnowledgeSource': MockKnowledgeSource,
            'KnowledgeResponse': MockKnowledgeResponse
        })()
        
        # Import the enhanced tool
        from tools.knowledge_base_tool import KnowledgeBaseTool
        
        # Test tool initialization
        kb_tool = KnowledgeBaseTool()
        logger.info("✓ Knowledge base tool initialized successfully")
        
        # Test freshness checking
        fresh_source = MockKnowledgeSource(
            source_id="test_1",
            title="Fresh Content",
            content="This is fresh content",
            category="test",
            last_updated=datetime.utcnow() - timedelta(days=5),  # 5 days ago (fresh)
            relevance_score=0.8
        )
        
        stale_source = MockKnowledgeSource(
            source_id="test_2", 
            title="Stale Content",
            content="This is stale content",
            category="test",
            last_updated=datetime.utcnow() - timedelta(days=45),  # 45 days ago (stale)
            relevance_score=0.7
        )
        
        assert kb_tool.is_content_fresh(fresh_source), "Fresh content should be marked as fresh"
        assert not kb_tool.is_content_fresh(stale_source), "Stale content should be marked as stale"
        logger.info("✓ Freshness checking works correctly")
        
        # Test source categorization
        sources = [fresh_source, stale_source]
        categorized = kb_tool.categorize_sources_by_freshness(sources)
        
        assert len(categorized['fresh']) == 1, "Should have 1 fresh source"
        assert len(categorized['stale']) == 1, "Should have 1 stale source"
        logger.info("✓ Source categorization works correctly")
        
        # Test answer synthesis
        synthesized = kb_tool.synthesize_answer(sources, "test query")
        assert isinstance(synthesized, str), "Synthesized answer should be a string"
        assert len(synthesized) > 0, "Synthesized answer should not be empty"
        assert "fresh content" in synthesized.lower(), "Should include fresh content"
        logger.info("✓ Answer synthesis works correctly")
        
        # Test confidence calculation
        confidence = kb_tool.calculate_confidence(sources, "test query")
        assert 0 <= confidence <= 1, "Confidence should be between 0 and 1"
        logger.info(f"✓ Confidence calculation works correctly: {confidence:.2f}")
        
        # Test fallback knowledge
        fallback_sources = kb_tool.get_fallback_knowledge("shipping", "shipping")
        assert isinstance(fallback_sources, list), "Fallback should return a list"
        assert len(fallback_sources) > 0, "Should have fallback sources for shipping"
        logger.info(f"✓ Fallback knowledge works correctly: {len(fallback_sources)} sources")
        
        # Test no knowledge response
        no_knowledge_response = kb_tool._generate_no_knowledge_response("unknown topic")
        assert isinstance(no_knowledge_response, str), "No knowledge response should be a string"
        assert "contact customer support" in no_knowledge_response.lower(), "Should suggest contacting support"
        logger.info("✓ No knowledge response generation works correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Knowledge base tool test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_features():
    """Test the enhanced features specifically"""
    logger.info("Testing enhanced knowledge base features...")
    
    try:
        # Test enhanced search with different query types
        test_queries = [
            ("shipping policy", "shipping"),
            ("return process", "returns"),
            ("payment methods", "payment"),
            ("account settings", "account"),
            ("unknown topic", None)
        ]
        
        # Mock the tool again for this test
        sys.path.insert(0, os.path.dirname(__file__))
        from tools.knowledge_base_tool import KnowledgeBaseTool
        
        kb_tool = KnowledgeBaseTool()
        
        for query, expected_category in test_queries:
            sources = kb_tool.get_fallback_knowledge(query)
            
            if expected_category:
                # Should find relevant sources
                assert len(sources) > 0, f"Should find sources for {query}"
                
                # Check if sources are relevant to the category
                relevant_sources = [s for s in sources if expected_category in s.category or expected_category in s.content.lower()]
                assert len(relevant_sources) > 0, f"Should find category-relevant sources for {query}"
                
                logger.info(f"✓ Query '{query}' found {len(sources)} sources")
            else:
                # May or may not find sources for unknown topics
                logger.info(f"✓ Query '{query}' handled appropriately")
        
        # Test enhanced synthesis with multiple sources
        shipping_sources = kb_tool.get_fallback_knowledge("shipping information", "shipping")
        if len(shipping_sources) > 1:
            synthesis = kb_tool.synthesize_answer(shipping_sources, "shipping information")
            
            # Should include freshness information
            assert "source" in synthesis.lower() or "information" in synthesis.lower(), "Should include source attribution"
            logger.info("✓ Multi-source synthesis includes proper attribution")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Enhanced features test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all knowledge base tool tests"""
    logger.info("=" * 60)
    logger.info("ENHANCED KNOWLEDGE BASE TOOL TEST")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Functionality", test_knowledge_base_tool_basic),
        ("Enhanced Features", test_enhanced_features)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All enhanced knowledge base tool tests passed!")
        return True
    else:
        logger.warning(f"⚠ {total - passed} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)