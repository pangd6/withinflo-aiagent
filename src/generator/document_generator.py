"""
Document generator for producing JSON and Markdown documentation outputs.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import jinja2
from loguru import logger
from pydantic import HttpUrl

from src.models.schema import QADocumentation, UIElement, TestCase


class DocumentGenerator:
    """
    Generates structured documentation in JSON and Markdown formats.
    """
    
    def __init__(self):
        # Initialize Jinja2 template environment
        self.template_env = jinja2.Environment(
            loader=jinja2.PackageLoader('src.generator.templates', ''),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_json(self, qa_doc: QADocumentation) -> str:
        """
        Generate JSON documentation output.
        
        Args:
            qa_doc: QA documentation data
            
        Returns:
            JSON string
        """
        try:
            # Convert to dict
            doc_dict = qa_doc.dict()
            
            # Convert datetime to ISO format string
            if isinstance(doc_dict['analysis_timestamp'], datetime):
                doc_dict['analysis_timestamp'] = doc_dict['analysis_timestamp'].isoformat()
            
            # Convert any HttpUrl objects to strings
            doc_dict['source_url'] = str(doc_dict['source_url'])
            
            # Generate formatted JSON
            json_str = json.dumps(doc_dict, indent=2)
            logger.info(f"Generated JSON documentation for {qa_doc.source_url}")
            
            return json_str
        except Exception as e:
            logger.error(f"Error generating JSON documentation: {e}")
            return "{}"
    
    def generate_markdown(self, qa_doc: QADocumentation) -> str:
        """
        Generate Markdown documentation output.
        
        Args:
            qa_doc: QA documentation data
            
        Returns:
            Markdown string
        """
        try:
            # Load the template
            template = self.template_env.get_template('qa_doc_template.md')
            
            # Prepare data for template
            template_data = {
                'source_url': str(qa_doc.source_url),
                'analysis_timestamp': qa_doc.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'page_title': qa_doc.page_title or 'Unknown',
                'test_cases': self._organize_test_cases(qa_doc.generated_test_cases, qa_doc.identified_elements)
            }
            
            # Render the template
            markdown_str = template.render(**template_data)
            logger.info(f"Generated Markdown documentation for {qa_doc.source_url}")
            
            return markdown_str
        except Exception as e:
            logger.error(f"Error generating Markdown documentation: {e}")
            return f"# Error Generating Documentation\n\nError: {str(e)}"
    
    def _organize_test_cases(
        self, 
        test_cases: List[TestCase], 
        elements: List[UIElement]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize test cases by type and prepare for template rendering.
        
        Args:
            test_cases: List of test cases
            elements: List of UI elements
            
        Returns:
            Dict of organized test cases by type
        """
        # Create a lookup dict for elements by ID
        element_map = {e.element_id: e for e in elements}
        
        # Group test cases by type
        organized = {
            'functional': [],
            'usability': [],
            'edge_case': [],
            'accessibility_check': []
        }
        
        for tc in test_cases:
            # Convert test case to dict and add additional info
            tc_dict = tc.dict()
            
            # Add element details if related to an element
            if tc.related_element_id and tc.related_element_id in element_map:
                element = element_map[tc.related_element_id]
                tc_dict['element_details'] = {
                    'element_type': element.element_type.value,
                    'selector': element.selector,
                    'visible_text': element.visible_text
                }
            
            # Add to organized dict by type
            tc_type = tc.type.value
            if tc_type in organized:
                organized[tc_type].append(tc_dict)
            else:
                organized[tc_type] = [tc_dict]
        
        # Sort each category by priority (high, medium, low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        for category in organized.values():
            category.sort(key=lambda x: priority_order.get(x['priority'], 1))
        
        return organized


# Singleton instance
document_generator = DocumentGenerator() 