"""
Celery tasks for QA Documentation Generator.
"""

import asyncio
from typing import Dict, Any, List, Optional

from celery import Celery
from celery.utils.log import get_task_logger
from loguru import logger
from pydantic import HttpUrl, ValidationError

from src.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from src.models.schema import QADocumentation, JobStatus
from src.crawler.website_analyzer import website_analyzer
from src.analysis.test_case_generator import test_case_generator
from src.generator.document_generator import document_generator
from src.db.mongodb import mongodb
from src.db.redis_client import redis_client


# Initialize Celery app
celery_app = Celery(
    'qa_doc_generator',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Initialize logger
task_logger = get_task_logger(__name__)


@celery_app.task(name="process_url")
def process_url(job_id: str, url: str, auth_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a URL to generate QA documentation.
    
    Args:
        job_id: The job ID
        url: The URL to process
        auth_config: Optional authentication configuration
        
    Returns:
        Dict with job status and any error message
    """
    task_logger.info(f"Processing URL: {url} for job {job_id}")
    
    try:
        # Connect to databases if not already connected
        _ensure_connections()
        
        # Update job status
        mongodb.update_job_status(job_id, JobStatus.PROCESSING)
        
        # Run the analysis process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Analyze the URL
            page_title, elements = loop.run_until_complete(
                website_analyzer.analyze_url(url, auth_config)
            )
            
            if not elements:
                raise Exception(f"No UI elements found at URL: {url}")
            
            # Generate test cases
            test_cases = test_case_generator.generate_test_cases(url, page_title or "Unknown", elements)
            
            if not test_cases:
                task_logger.warning(f"No test cases generated for URL: {url}")
            
            # Create QA documentation
            qa_doc = QADocumentation(
                source_url=url,
                page_title=page_title,
                identified_elements=elements,
                generated_test_cases=test_cases
            )
            
            # Generate JSON and Markdown
            json_output = document_generator.generate_json(qa_doc)
            markdown_output = document_generator.generate_markdown(qa_doc)
            
            # Save documentation to MongoDB
            doc_id = mongodb.save_qa_documentation(job_id, qa_doc)
            
            task_logger.info(f"Completed processing URL: {url} for job {job_id}")
            return {
                "status": "completed",
                "url": url,
                "doc_id": doc_id,
                "element_count": len(elements),
                "test_case_count": len(test_cases)
            }
        finally:
            # Close the event loop
            loop.close()
            
            # Close the website analyzer browser
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(website_analyzer.close())
            finally:
                loop.close()
    except Exception as e:
        error_msg = f"Error processing URL {url}: {str(e)}"
        task_logger.error(error_msg)
        return {"status": "failed", "url": url, "error": error_msg}


@celery_app.task(name="process_job")
def process_job(job_id: str) -> Dict[str, Any]:
    """
    Process a job with multiple URLs.
    
    Args:
        job_id: The job ID
        
    Returns:
        Dict with job status and results
    """
    task_logger.info(f"Processing job: {job_id}")
    
    try:
        # Connect to databases if not already connected
        _ensure_connections()
        
        # Get job details
        job = mongodb.get_job(job_id)
        if not job:
            raise Exception(f"Job not found: {job_id}")
        
        # Extract job details
        urls = job.get("urls", [])
        auth_config = job.get("auth_config")
        
        # Update job status
        mongodb.update_job_status(job_id, JobStatus.PROCESSING)
        
        # Process each URL
        results = []
        for url in urls:
            # Process the URL (this will be executed in the current task)
            result = process_url(job_id, url, auth_config)
            results.append(result)
        
        # Update job status
        success_count = sum(1 for r in results if r.get("status") == "completed")
        if success_count == len(urls):
            mongodb.update_job_status(job_id, JobStatus.COMPLETED)
            status = "completed"
        elif success_count > 0:
            mongodb.update_job_status(
                job_id, 
                JobStatus.COMPLETED, 
                f"Partially completed: {success_count}/{len(urls)} URLs processed"
            )
            status = "partially_completed"
        else:
            mongodb.update_job_status(job_id, JobStatus.FAILED, "All URLs failed processing")
            status = "failed"
        
        return {
            "status": status,
            "job_id": job_id,
            "url_count": len(urls),
            "success_count": success_count,
            "results": results
        }
    except Exception as e:
        error_msg = f"Error processing job {job_id}: {str(e)}"
        task_logger.error(error_msg)
        mongodb.update_job_status(job_id, JobStatus.FAILED, error_msg)
        return {"status": "failed", "job_id": job_id, "error": error_msg}


def _ensure_connections() -> None:
    """Ensure database connections are established."""
    try:
        mongodb.connect()
        redis_client.connect()
    except Exception as e:
        task_logger.error(f"Error connecting to databases: {e}")
        raise 