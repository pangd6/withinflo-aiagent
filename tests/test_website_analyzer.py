"""
Tests for the website analyzer module.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.crawler.website_analyzer import WebsiteAnalyzer
from src.models.schema import ElementType, Position


@pytest.fixture
def mock_playwright():
    """Create a mock for Playwright."""
    with patch('src.crawler.website_analyzer.async_playwright') as mock:
        # Setup mock playwright
        mock_playwright_instance = AsyncMock()
        mock.return_value = mock_playwright_instance
        
        # Setup mock browser
        mock_browser = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        
        # Setup mock context
        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        
        # Setup mock page
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        
        # Setup page title
        mock_page.title.return_value = "Test Page"
        
        # Setup page content
        mock_page.content.return_value = "<html><body><h1>Test Page</h1></body></html>"
        
        # Setup mock element handles
        mock_h1_handle = AsyncMock()
        mock_h1_handle.evaluate.side_effect = lambda script, *args: (
            "h1" if "tagName" in script else 
            "h1.page-title" if "selector" in script else
            {"id": "page-title"} if "attributes" in script else
            "Test Page" if "textContent" in script else None
        )
        mock_h1_handle.bounding_box.return_value = {"x": 10, "y": 20, "width": 100, "height": 50}
        
        mock_button_handle = AsyncMock()
        mock_button_handle.evaluate.side_effect = lambda script, *args: (
            "button" if "tagName" in script else 
            "button#submit-btn" if "selector" in script else
            {"id": "submit-btn", "type": "submit"} if "attributes" in script else
            "Submit" if "textContent" in script else None
        )
        mock_button_handle.bounding_box.return_value = {"x": 50, "y": 100, "width": 80, "height": 30}
        
        # Setup query selectors
        async def mock_query_selector_all(selector):
            if "h1" in selector:
                return [mock_h1_handle]
            elif "button" in selector:
                return [mock_button_handle]
            return []
        
        mock_page.query_selector_all.side_effect = mock_query_selector_all
        
        yield mock


@pytest.mark.asyncio
async def test_analyze_url(mock_playwright):
    """Test analyzing a URL."""
    # Create analyzer
    analyzer = WebsiteAnalyzer()
    
    # Mock Redis
    with patch('src.crawler.website_analyzer.redis_client') as mock_redis:
        mock_redis.get_dom_snapshot.return_value = None
        mock_redis.check_rate_limit.return_value = True
        
        # Analyze URL
        page_title, elements = await analyzer.analyze_url("https://example.com")
        
        # Verify results
        assert page_title == "Test Page"
        assert len(elements) > 0
        
        # Check for heading element
        heading_elements = [e for e in elements if e.element_type == ElementType.HEADING]
        assert len(heading_elements) > 0
        heading = heading_elements[0]
        assert heading.visible_text == "Test Page"
        assert heading.selector == "h1.page-title"
        assert isinstance(heading.position, Position)
        assert heading.position.x == 10
        assert heading.position.y == 20
        
        # Check for button element
        button_elements = [e for e in elements if e.element_type == ElementType.BUTTON]
        assert len(button_elements) > 0
        button = button_elements[0]
        assert button.visible_text == "Submit"
        assert button.selector == "button#submit-btn"
        assert isinstance(button.position, Position)
        
        # Clean up
        await analyzer.close() 