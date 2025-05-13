"""
Website analyzer for crawling and analyzing web pages.
"""

import asyncio
import uuid
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Tuple

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, ElementHandle
from pydantic import HttpUrl
from loguru import logger

from src.models.schema import UIElement, Position, ElementType, AuthConfig
from src.config import DEFAULT_CRAWL_TIMEOUT, DEFAULT_WAIT_FOR_LOAD, DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE
from src.db.redis_client import redis_client


class WebsiteAnalyzer:
    """
    Analyzes websites using Playwright to extract UI elements and their properties.
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    async def initialize(self) -> None:
        """Initialize the Playwright browser."""
        try:
            logger.info("Initializing Playwright browser")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch()
            self.context = await self.browser.new_context()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            if self.playwright:
                await self.playwright.stop()
            raise
    
    async def close(self) -> None:
        """Close the Playwright browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Closed Playwright browser")
    
    def _get_domain(self, url: str) -> str:
        """
        Get the domain from a URL.
        
        Args:
            url: The URL
            
        Returns:
            The domain name
        """
        return urlparse(url).netloc
    
    async def _setup_authentication(self, page: Page, auth_config: Optional[Dict[str, Any]]) -> None:
        """
        Set up authentication for the page.
        
        Args:
            page: The Playwright page
            auth_config: Authentication configuration
        """
        if not auth_config:
            return
        
        try:
            auth_type = auth_config.get("auth_type", "basic")
            
            if auth_type == "basic":
                username = auth_config.get("username")
                password = auth_config.get("password")
                
                if username and password:
                    await page.authenticate({"username": username, "password": password})
                    logger.info("Set up basic authentication")
            
            elif auth_type == "session_token":
                token_type = auth_config.get("token_type")
                token_name = auth_config.get("token_name")
                token_value = auth_config.get("token_value")
                
                if token_type and token_name and token_value:
                    if token_type == "cookie":
                        await page.context.add_cookies([{
                            "name": token_name,
                            "value": token_value,
                            "url": page.url
                        }])
                        logger.info(f"Set up cookie authentication with token: {token_name}")
                    
                    elif token_type == "bearer":
                        # For bearer tokens, we'll set the header when navigating
                        await page.set_extra_http_headers({
                            token_name: f"Bearer {token_value}"
                        })
                        logger.info(f"Set up bearer token authentication with header: {token_name}")
        except Exception as e:
            logger.error(f"Authentication setup error: {e}")
            raise
    
    async def analyze_url(
        self, 
        url: str, 
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: int = DEFAULT_CRAWL_TIMEOUT,
        wait_for_load: int = DEFAULT_WAIT_FOR_LOAD,
        rate_limit: int = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE
    ) -> Tuple[Optional[str], List[UIElement]]:
        """
        Analyze a URL to extract UI elements.
        
        Args:
            url: The URL to analyze
            auth_config: Optional authentication configuration
            timeout: Timeout in seconds for page load
            wait_for_load: Time to wait for dynamic content to load
            rate_limit: Rate limit for requests per minute
            
        Returns:
            A tuple of (page_title, list of UI elements)
        """
        # Check cache first
        cached_content = redis_client.get_dom_snapshot(url)
        if cached_content:
            logger.info(f"Using cached DOM for URL: {url}")
            # TODO: Parse cached DOM content
            # For MVP, we'll skip cache handling and always fetch fresh content
        
        # Check rate limiting
        domain = self._get_domain(url)
        if not redis_client.check_rate_limit(domain, rate_limit):
            logger.warning(f"Rate limit exceeded for domain: {domain}. Delaying request.")
            await asyncio.sleep(60)  # Wait a minute before retrying
        
        if not self.browser:
            await self.initialize()
        
        page = None
        elements = []
        page_title = None
        
        try:
            logger.info(f"Analyzing URL: {url}")
            page = await self.context.new_page()
            
            # Set up authentication if provided
            await self._setup_authentication(page, auth_config)
            
            # Navigate to the URL
            response = await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            
            if not response:
                logger.error(f"Failed to load URL: {url}")
                return None, []
            
            if response.status >= 400:
                logger.error(f"HTTP error {response.status} for URL: {url}")
                return None, []
            
            # Wait for dynamic content to load
            await asyncio.sleep(wait_for_load)
            
            # Get page title
            page_title = await page.title()
            logger.info(f"Loaded page: {page_title} ({url})")
            
            # Extract UI elements
            elements = await self._extract_ui_elements(page)
            logger.info(f"Extracted {len(elements)} UI elements from {url}")
            
            # Cache the DOM content
            html_content = await page.content()
            redis_client.cache_dom_snapshot(url, html_content)
            
            return page_title, elements
            
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {e}")
            return None, []
        finally:
            if page:
                await page.close()
    
    async def _extract_ui_elements(self, page: Page) -> List[UIElement]:
        """
        Extract UI elements from a page.
        
        Args:
            page: The Playwright page
            
        Returns:
            List of UI elements
        """
        elements = []
        
        # Define selectors for different types of elements
        selectors = {
            "button": "button, input[type='button'], input[type='submit'], input[type='reset']",
            "input_text": "input[type='text'], input:not([type])",
            "input_password": "input[type='password']",
            "input_email": "input[type='email']",
            "input_number": "input[type='number']",
            "input_checkbox": "input[type='checkbox']",
            "input_radio": "input[type='radio']",
            "select_dropdown": "select",
            "textarea": "textarea",
            "link": "a[href]",
            "form": "form",
            "image": "img",
            "heading": "h1, h2, h3, h4, h5, h6",
            "paragraph": "p",
            "list": "ul, ol",
            "table": "table",
            "label": "label",
            "iframe": "iframe",
            "video": "video"
        }
        
        # Process each type of element
        for element_type_str, selector in selectors.items():
            element_type = getattr(ElementType, element_type_str.upper(), ElementType.GENERAL_CONTAINER)
            
            try:
                # Find all elements matching the selector
                handles = await page.query_selector_all(selector)
                
                for handle in handles:
                    try:
                        element = await self._process_element_handle(handle, element_type)
                        if element:
                            elements.append(element)
                    except Exception as e:
                        logger.error(f"Error processing {element_type_str} element: {e}")
            except Exception as e:
                logger.error(f"Error querying {element_type_str} elements: {e}")
        
        # Add special handling for containers with roles or significant content
        container_selector = "div[role], span[role], div.container, div.section, div.content"
        try:
            containers = await page.query_selector_all(container_selector)
            for container in containers:
                try:
                    element = await self._process_element_handle(container, ElementType.GENERAL_CONTAINER)
                    if element:
                        elements.append(element)
                except Exception as e:
                    logger.error(f"Error processing container element: {e}")
        except Exception as e:
            logger.error(f"Error querying container elements: {e}")
        
        return elements
    
    async def _process_element_handle(
        self, 
        handle: ElementHandle, 
        element_type: ElementType
    ) -> Optional[UIElement]:
        """
        Process an element handle to extract its properties.
        
        Args:
            handle: The Playwright element handle
            element_type: The type of element
            
        Returns:
            A UIElement object, or None if processing failed
        """
        try:
            # Generate a unique ID for the element
            element_id = str(uuid.uuid4())
            
            # Get element properties
            tag_name = await handle.evaluate("el => el.tagName.toLowerCase()")
            
            # Get a selector for the element
            selector = await handle.evaluate('''element => {
                // Try to get an ID-based selector
                if (element.id) {
                    return `#${element.id}`;
                }
                
                // Try to get a unique selector using attributes
                if (element.hasAttribute('name')) {
                    const name = element.getAttribute('name');
                    return `${element.tagName.toLowerCase()}[name='${name}']`;
                }
                
                if (element.hasAttribute('data-testid')) {
                    const testId = element.getAttribute('data-testid');
                    return `${element.tagName.toLowerCase()}[data-testid='${testId}']`;
                }
                
                // Fallback to a more complex selector
                // This is a simplified version and may not be unique in all cases
                let selector = element.tagName.toLowerCase();
                if (element.className && typeof element.className === 'string' && element.className.trim()) {
                    const classes = element.className.trim().split(/\\s+/).map(c => `.${c}`).join('');
                    selector += classes;
                }
                return selector;
            }''')
            
            # Get element attributes
            attributes = await handle.evaluate('''element => {
                const attrs = {};
                for (const attr of element.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }''')
            
            # Get visible text
            visible_text = await handle.evaluate("element => element.textContent?.trim() || null")
            
            # Get element position and dimensions
            bounding_box = await handle.bounding_box()
            position = None
            if bounding_box:
                position = Position(
                    x=int(bounding_box["x"]),
                    y=int(bounding_box["y"]),
                    width=int(bounding_box["width"]),
                    height=int(bounding_box["height"])
                )
            
            # Create the UI Element
            return UIElement(
                element_id=element_id,
                element_type=element_type,
                selector=selector,
                attributes=attributes,
                visible_text=visible_text,
                position=position
            )
        except Exception as e:
            logger.error(f"Error processing element: {e}")
            return None


# Singleton instance
website_analyzer = WebsiteAnalyzer() 