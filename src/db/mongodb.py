"""
MongoDB connection and operations.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from bson.objectid import ObjectId

from loguru import logger
from src.config import MONGODB_URI, MONGODB_DB
from src.models.schema import JobStatus, QADocumentation, JobRequest


class MongoDB:
    """MongoDB database connection and operations."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.jobs_collection = None
        self.qa_docs_collection = None
        self.websites_collection = None
        self.pages_collection = None
        self.ui_elements_collection = None
        self.test_cases_collection = None
    
    def connect(self) -> None:
        """Connect to MongoDB and initialize collections."""
        try:
            logger.info(f"Connecting to MongoDB at {MONGODB_URI}")
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client[MONGODB_DB]
            
            # Initialize collections
            self.jobs_collection = self.db.jobs
            self.qa_docs_collection = self.db.qa_docs
            self.websites_collection = self.db.websites
            self.pages_collection = self.db.pages
            self.ui_elements_collection = self.db.ui_elements
            self.test_cases_collection = self.db.test_cases
            
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def create_job(self, job_request: JobRequest) -> str:
        """
        Create a new job for URL processing.
        
        Args:
            job_request: The job request data
            
        Returns:
            The job ID as a string
        """
        job_data = {
            "urls": [str(url) for url in job_request.urls],
            "status": JobStatus.PENDING.value,
            "created_at": datetime.utcnow(),
            "auth_config": job_request.auth_config,
            "rate_limit": job_request.rate_limit_requests_per_minute
        }
        
        result = self.jobs_collection.insert_one(job_data)
        job_id = str(result.inserted_id)
        logger.info(f"Created job with ID: {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            The job data as a dictionary, or None if not found
        """
        try:
            job = self.jobs_collection.find_one({"_id": ObjectId(job_id)})
            if job:
                job["_id"] = str(job["_id"])
            return job
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: JobStatus, message: Optional[str] = None) -> bool:
        """
        Update a job's status.
        
        Args:
            job_id: The job ID
            status: The new status
            message: Optional status message
            
        Returns:
            True if successful, False otherwise
        """
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        if message:
            update_data["message"] = message
        
        try:
            result = self.jobs_collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            return False
    
    def save_qa_documentation(self, job_id: str, qa_doc: QADocumentation) -> str:
        """
        Save generated QA documentation to the database.
        
        Args:
            job_id: The job ID associated with this documentation
            qa_doc: The QA documentation data
            
        Returns:
            The document ID
        """
        doc_data = qa_doc.dict()
        doc_data["job_id"] = job_id
        doc_data["created_at"] = datetime.utcnow()
        
        result = self.qa_docs_collection.insert_one(doc_data)
        doc_id = str(result.inserted_id)
        logger.info(f"Saved QA documentation with ID: {doc_id}")
        return doc_id
    
    def get_qa_documentation(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get QA documentation by ID.
        
        Args:
            doc_id: The documentation ID
            
        Returns:
            The documentation data as a dictionary, or None if not found
        """
        try:
            doc = self.qa_docs_collection.find_one({"_id": ObjectId(doc_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error getting QA documentation {doc_id}: {e}")
            return None
    
    def get_qa_docs_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all QA documentation for a specific job.
        
        Args:
            job_id: The job ID
            
        Returns:
            List of QA documentation dictionaries
        """
        try:
            docs = list(self.qa_docs_collection.find({"job_id": job_id}))
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            return docs
        except Exception as e:
            logger.error(f"Error getting QA docs for job {job_id}: {e}")
            return []
    
    def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")


# Singleton instance
mongodb = MongoDB() 