"""
FastAPI application for the QA Documentation Generator.
"""

from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Path, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import HttpUrl

from loguru import logger
from celery.result import AsyncResult

from src.models.schema import JobRequest, JobResponse, JobStatus
from src.db.mongodb import mongodb
from src.db.redis_client import redis_client
from src.config import DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE, validate_config
from src.worker.tasks import process_job


# Create the FastAPI app
app = FastAPI(
    title="AI-Powered QA Documentation Generator",
    description="Generates comprehensive QA documentation from website analysis",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Connect to databases on startup."""
    try:
        # Validate configuration
        valid, error_message = validate_config()
        if not valid:
            logger.error(f"Invalid configuration: {error_message}")
            raise RuntimeError(f"Invalid configuration: {error_message}")
        
        # Connect to databases
        mongodb.connect()
        redis_client.connect()
        logger.info("API started and connected to databases")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    try:
        mongodb.close()
        redis_client.close()
        logger.info("API shutdown and closed database connections")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


@app.post("/jobs", response_model=JobResponse, summary="Create a new job")
async def create_job(job_request: JobRequest):
    """
    Create a new job to process URLs and generate QA documentation.
    
    - **urls**: List of URLs to process
    - **auth_config**: Optional authentication configuration
    - **rate_limit_requests_per_minute**: Optional rate limit (requests per minute per domain)
    """
    try:
        # Set default rate limit if not provided
        if not job_request.rate_limit_requests_per_minute:
            job_request.rate_limit_requests_per_minute = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE
        
        # Create a job in the database
        job_id = mongodb.create_job(job_request)
        
        # Start job processing in the background (Celery task)
        process_job.delay(job_id)
        
        # Return the job information
        job_data = mongodb.get_job(job_id)
        
        # Create response
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            urls=[str(url) for url in job_request.urls],
            created_at=job_data["created_at"],
            message="Job created and scheduled for processing"
        )
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")


@app.get("/jobs/{job_id}", response_model=JobResponse, summary="Get job status")
async def get_job_status(job_id: str = Path(..., description="The job ID")):
    """
    Get the status of a job by ID.
    """
    job = mongodb.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus(job["status"]),
        urls=job["urls"],
        created_at=job["created_at"],
        updated_at=job.get("updated_at"),
        message=job.get("message")
    )


@app.get("/jobs/{job_id}/results", response_model=List[Dict[str, Any]], summary="Get job results")
async def get_job_results(job_id: str = Path(..., description="The job ID")):
    """
    Get the results for a job, including links to the generated documentation.
    """
    job = mongodb.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Get QA documentation generated for this job
    qa_docs = mongodb.get_qa_docs_by_job(job_id)
    
    # Format results
    results = []
    for doc in qa_docs:
        results.append({
            "doc_id": doc["_id"],
            "url": doc["source_url"],
            "page_title": doc.get("page_title", "Unknown"),
            "analysis_timestamp": doc["analysis_timestamp"],
            "element_count": len(doc.get("identified_elements", [])),
            "test_case_count": len(doc.get("generated_test_cases", [])),
            "links": {
                "json": f"/docs/{doc['_id']}/json",
                "markdown": f"/docs/{doc['_id']}/markdown"
            }
        })
    
    return results


@app.get("/docs/{doc_id}/json", response_class=PlainTextResponse, summary="Get JSON documentation")
async def get_json_doc(doc_id: str = Path(..., description="The documentation ID")):
    """
    Get the generated QA documentation in JSON format.
    """
    doc = mongodb.get_qa_documentation(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documentation {doc_id} not found")
    
    # Clean up MongoDB-specific fields
    doc.pop("_id", None)
    doc.pop("job_id", None)
    
    return JSONResponse(content=doc)


@app.get("/docs/{doc_id}/markdown", response_class=PlainTextResponse, summary="Get Markdown documentation")
async def get_markdown_doc(doc_id: str = Path(..., description="The documentation ID")):
    """
    Get the generated QA documentation in Markdown format.
    """
    doc = mongodb.get_qa_documentation(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documentation {doc_id} not found")
    
    # Generate Markdown from the stored data
    from src.models.schema import QADocumentation
    from src.generator.document_generator import document_generator
    
    try:
        # Convert the MongoDB document to a QADocumentation object
        qa_doc = QADocumentation(
            source_url=doc["source_url"],
            analysis_timestamp=doc["analysis_timestamp"],
            page_title=doc.get("page_title"),
            identified_elements=doc.get("identified_elements", []),
            generated_test_cases=doc.get("generated_test_cases", [])
        )
        
        # Generate Markdown
        markdown = document_generator.generate_markdown(qa_doc)
        return PlainTextResponse(content=markdown)
    except Exception as e:
        logger.error(f"Error generating Markdown: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating Markdown documentation: {str(e)}"
        )


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Check the health of the API and its dependencies.
    """
    try:
        # Check MongoDB connection
        mongodb_health = {"status": "ok"}
        try:
            if not mongodb.client:
                mongodb.connect()
            mongodb.client.admin.command('ping')
        except Exception as e:
            mongodb_health = {"status": "error", "message": str(e)}
        
        # Check Redis connection
        redis_health = {"status": "ok"}
        try:
            if not redis_client.client:
                redis_client.connect()
            redis_client.client.ping()
        except Exception as e:
            redis_health = {"status": "error", "message": str(e)}
        
        # Overall status
        status = "healthy" if mongodb_health["status"] == "ok" and redis_health["status"] == "ok" else "unhealthy"
        
        return {
            "status": status,
            "version": app.version,
            "dependencies": {
                "mongodb": mongodb_health,
                "redis": redis_health
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)} 