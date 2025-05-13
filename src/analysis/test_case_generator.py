"""
Test case generator using OpenAI's GPT model.
"""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple

import openai
from loguru import logger
from pydantic import ValidationError

from src.config import LLM_API_KEY, LLM_MODEL
from src.models.schema import UIElement, TestCase, TestCaseType, TestCasePriority, TestStep


class TestCaseGenerator:
    """
    Generates test cases using OpenAI's GPT model based on UI elements.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the test case generator.
        
        Args:
            api_key: OpenAI API key (defaults to config)
            model: OpenAI model to use (defaults to config)
        """
        self.api_key = api_key or LLM_API_KEY
        self.model = model or LLM_MODEL
        
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.error("No OpenAI API key provided")
    
    def generate_test_cases(
        self, 
        url: str, 
        page_title: str, 
        elements: List[UIElement]
    ) -> List[TestCase]:
        """
        Generate test cases for a list of UI elements.
        
        Args:
            url: The URL of the page
            page_title: The title of the page
            elements: List of UI elements
            
        Returns:
            List of generated test cases
        """
        all_test_cases = []
        
        try:
            # First, generate overall functional test cases for the page
            page_test_cases = self._generate_page_level_test_cases(url, page_title, elements)
            all_test_cases.extend(page_test_cases)
            
            # Generate element-specific test cases
            for element in elements:
                element_test_cases = self._generate_element_test_cases(url, page_title, element, elements)
                all_test_cases.extend(element_test_cases)
            
            logger.info(f"Generated {len(all_test_cases)} test cases for {url}")
            return all_test_cases
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return []
    
    def _generate_page_level_test_cases(
        self, 
        url: str, 
        page_title: str, 
        elements: List[UIElement]
    ) -> List[TestCase]:
        """
        Generate page-level test cases.
        
        Args:
            url: The URL of the page
            page_title: The title of the page
            elements: List of UI elements
            
        Returns:
            List of generated test cases
        """
        try:
            # Create a summary of the page elements
            form_elements = [e for e in elements if e.element_type == "form"]
            button_elements = [e for e in elements if e.element_type == "button"]
            link_elements = [e for e in elements if e.element_type == "link"]
            input_elements = [e for e in elements if e.element_type.value.startswith("input_")]
            
            element_summary = {
                "forms": len(form_elements),
                "buttons": len(button_elements),
                "links": len(link_elements),
                "inputs": len(input_elements),
                "total_elements": len(elements)
            }
            
            # Create a prompt for the LLM
            prompt = self._create_page_level_prompt(url, page_title, element_summary)
            
            # Get response from OpenAI
            response = self._call_llm_api(prompt)
            
            # Parse the response
            if response:
                test_cases = self._parse_test_cases_response(response, url, None)
                logger.info(f"Generated {len(test_cases)} page-level test cases")
                return test_cases
            
            return []
        except Exception as e:
            logger.error(f"Error generating page-level test cases: {e}")
            return []
    
    def _generate_element_test_cases(
        self, 
        url: str, 
        page_title: str, 
        element: UIElement, 
        all_elements: List[UIElement]
    ) -> List[TestCase]:
        """
        Generate test cases for a specific UI element.
        
        Args:
            url: The URL of the page
            page_title: The title of the page
            element: The UI element to generate test cases for
            all_elements: All UI elements on the page (for context)
            
        Returns:
            List of generated test cases
        """
        try:
            # Don't generate test cases for non-interactive or content elements
            if element.element_type in [
                "paragraph", "heading", "image", "video", "general_container"
            ] and element.element_type.value != "link":
                return []
            
            # Create a prompt for the LLM
            prompt = self._create_element_prompt(url, page_title, element, all_elements)
            
            # Get response from OpenAI
            response = self._call_llm_api(prompt)
            
            # Parse the response
            if response:
                test_cases = self._parse_test_cases_response(response, url, element.element_id)
                logger.info(f"Generated {len(test_cases)} test cases for element {element.element_id}")
                return test_cases
            
            return []
        except Exception as e:
            logger.error(f"Error generating test cases for element {element.element_id}: {e}")
            return []
    
    def _create_page_level_prompt(
        self, 
        url: str, 
        page_title: str, 
        element_summary: Dict[str, int]
    ) -> str:
        """
        Create a prompt for generating page-level test cases.
        
        Args:
            url: The URL of the page
            page_title: The title of the page
            element_summary: Summary of elements on the page
            
        Returns:
            The prompt string
        """
        prompt = f"""You are an expert QA engineer. Generate comprehensive test cases for the following web page:

URL: {url}
Page Title: {page_title}
Element Summary: {json.dumps(element_summary, indent=2)}

Please generate 3-5 test cases for this page that cover the following:
1. Basic page functionality (e.g., page load, title verification)
2. Core user flows or journeys that can be identified from the page structure
3. High-level usability aspects of the page

Each test case should have:
- A unique test case ID (starting with TC_PAGE_)
- A descriptive title
- Type (one of: functional, usability, edge_case, accessibility_check)
- Priority (one of: high, medium, low)
- Description
- Preconditions (if any)
- Steps (including action and expected result for each step)

Format your response as a valid JSON array of test cases. Example format:
[
  {{
    "test_case_id": "TC_PAGE_001",
    "test_case_title": "Verify page loads successfully with correct title",
    "type": "functional",
    "priority": "high",
    "description": "This test verifies that the page loads correctly and displays the expected title.",
    "preconditions": ["User has internet connectivity"],
    "steps": [
      {{
        "step_number": 1,
        "action": "Navigate to {url}",
        "expected_result": "The page loads successfully without errors"
      }},
      {{
        "step_number": 2,
        "action": "Observe the page title",
        "expected_result": "The page title is '{page_title}'"
      }}
    ]
  }}
]

Ensure all the generated test cases are realistic, detailed and would be valuable for testing this page."""
        
        return prompt
    
    def _create_element_prompt(
        self, 
        url: str, 
        page_title: str, 
        element: UIElement, 
        all_elements: List[UIElement]
    ) -> str:
        """
        Create a prompt for generating element-specific test cases.
        
        Args:
            url: The URL of the page
            page_title: The title of the page
            element: The UI element
            all_elements: All UI elements on the page
            
        Returns:
            The prompt string
        """
        # Find related elements (e.g., label for an input)
        related_elements = []
        if element.element_type.value.startswith("input_"):
            # Look for associated labels
            for other in all_elements:
                if other.element_type == "label" and 'for' in other.attributes:
                    if other.attributes.get('for') == element.attributes.get('id'):
                        related_elements.append(other)
        
        # Create element description
        element_json = element.json()
        related_json = [e.json() for e in related_elements]
        
        # Create decision tree logic based on element type
        test_case_guidance = self._get_test_case_guidance(element)
        
        prompt = f"""You are an expert QA engineer. Generate comprehensive test cases for the following web element:

URL: {url}
Page Title: {page_title}
Element: {element_json}
Related Elements: {related_json if related_elements else "None"}

{test_case_guidance}

Each test case should have:
- A unique test case ID (starting with TC_FUNC_, TC_USA_, or TC_EDGE_ depending on type)
- A descriptive title
- Type (one of: functional, usability, edge_case)
- Priority (one of: high, medium, low)
- Description
- Preconditions (if applicable)
- Steps (including action and expected result for each step)

Format your response as a valid JSON array of test cases. Example format:
[
  {{
    "test_case_id": "TC_FUNC_001",
    "test_case_title": "Verify input accepts valid data",
    "type": "functional",
    "priority": "high",
    "description": "This test verifies that the input field accepts valid data.",
    "preconditions": ["User is on the page"],
    "steps": [
      {{
        "step_number": 1,
        "action": "Enter 'Test Data' into the element",
        "expected_result": "The data is entered successfully"
      }},
      {{
        "step_number": 2,
        "action": "Click outside the input field",
        "expected_result": "The input field maintains the entered value"
      }}
    ]
  }}
]

Ensure all the generated test cases are realistic, detailed, and focused on this specific element."""
        
        return prompt
    
    def _get_test_case_guidance(self, element: UIElement) -> str:
        """
        Get guidance for test case generation based on element type.
        
        Args:
            element: The UI element
            
        Returns:
            Guidance text
        """
        element_type = element.element_type.value
        
        # Decision tree logic
        if element_type in ["input_text", "input_email", "input_password", "textarea"]:
            return """Based on this input element, generate the following types of test cases:
1. Functional tests for valid input
2. Functional tests for clearing input
3. Edge case tests for empty input (if required)
4. Edge case tests for min/max length (if determinable from attributes)
5. Edge case tests for invalid formats (especially for email/password)

For an input_email, consider test cases for:
- Valid email format
- Missing @ symbol
- Missing domain
- Special characters
- Very long email addresses"""

        elif element_type == "input_number":
            return """Based on this number input element, generate the following types of test cases:
1. Functional tests for valid numeric input
2. Edge cases for non-numeric input
3. Edge cases for out-of-range values (if min/max attributes exist)
4. Edge cases for decimal values (if relevant)
5. Test case for input field increment/decrement controls (if present)"""

        elif element_type in ["input_checkbox", "input_radio"]:
            return """Based on this checkbox/radio element, generate the following types of test cases:
1. Functional tests for selecting the element
2. Functional tests for de-selecting (if checkbox)
3. Usability tests for verifying visible label association
4. Test case for default state verification"""

        elif element_type == "button":
            button_text = element.visible_text or element.attributes.get('value', 'Button')
            return f"""Based on this button element with text "{button_text}", generate the following types of test cases:
1. Functional test for clicking the button and verifying an expected outcome
2. Usability test for button visibility and accessibility
3. If this appears to be a submit button in a form, include a test case for form submission"""

        elif element_type == "link":
            link_text = element.visible_text or "Link"
            href = element.attributes.get('href', '#')
            return f"""Based on this link element with text "{link_text}" and href "{href}", generate the following types of test cases:
1. Functional test for navigation: clicking the link and verifying navigation to the target
2. Usability test for link appearance and recognition
3. Edge case for broken link verification (if applicable)"""
            
        elif element_type == "select_dropdown":
            return """Based on this dropdown element, generate the following types of test cases:
1. Functional tests for selecting different options
2. Functional test for default selected option
3. Edge case for deselection (if applicable)
4. Usability test for dropdown appearance and option visibility"""
            
        elif element_type == "form":
            return """Based on this form element, generate the following types of test cases:
1. End-to-end functional test for form submission with valid data
2. Functional tests for submitting with mandatory fields empty
3. Edge cases for form reset functionality (if applicable)
4. Usability test for form layout and field organization"""
            
        else:
            return """Generate 2-3 test cases for this element covering:
1. Functional testing of primary actions possible with this element
2. Usability aspects of the element
3. Edge cases or error conditions if relevant"""
    
    def _call_llm_api(self, prompt: str) -> Optional[str]:
        """
        Call the OpenAI API to get test case suggestions.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            The API response content, or None if there was an error
        """
        if not self.api_key:
            logger.error("Cannot call OpenAI API: No API key")
            return None
        
        try:
            logger.info(f"Calling OpenAI API with model: {self.model}")
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert QA engineer who creates comprehensive test cases."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return content
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None
    
    def _parse_test_cases_response(
        self, 
        response: str, 
        url: str, 
        element_id: Optional[str]
    ) -> List[TestCase]:
        """
        Parse test cases from the LLM response.
        
        Args:
            response: The LLM response
            url: The URL of the page
            element_id: The element ID (None for page-level test cases)
            
        Returns:
            List of parsed test cases
        """
        try:
            # Extract JSON from the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                # If no JSON array found, try to parse the entire response
                json_content = response
            else:
                json_content = response[json_start:json_end]
            
            # Parse the JSON
            test_cases_data = json.loads(json_content)
            
            # Convert to TestCase objects
            test_cases = []
            for tc_data in test_cases_data:
                # Ensure the test case ID is unique
                if 'test_case_id' not in tc_data or not tc_data['test_case_id']:
                    tc_data['test_case_id'] = f"TC_{uuid.uuid4().hex[:8].upper()}"
                
                # Create steps
                steps = []
                if 'steps' in tc_data:
                    for step_data in tc_data['steps']:
                        step = TestStep(
                            step_number=step_data.get('step_number', 1),
                            action=step_data.get('action', 'No action provided'),
                            expected_result=step_data.get('expected_result', 'No expected result provided')
                        )
                        steps.append(step)
                
                # Create the test case
                test_case = TestCase(
                    test_case_id=tc_data.get('test_case_id'),
                    test_case_title=tc_data.get('test_case_title', 'No title provided'),
                    type=TestCaseType(tc_data.get('type', 'functional').lower()),
                    priority=TestCasePriority(tc_data.get('priority', 'medium').lower()),
                    description=tc_data.get('description', 'No description provided'),
                    preconditions=tc_data.get('preconditions', []),
                    steps=steps,
                    related_element_id=element_id
                )
                
                test_cases.append(test_case)
            
            return test_cases
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            return []
        except ValidationError as e:
            logger.error(f"Validation error creating TestCase objects: {e}")
            return []
        except Exception as e:
            logger.error(f"Unknown error parsing test cases: {e}")
            return []


# Singleton instance
test_case_generator = TestCaseGenerator() 